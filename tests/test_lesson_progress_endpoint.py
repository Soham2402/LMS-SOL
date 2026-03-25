"""Tests for the lesson progress upsert endpoint and cascade behavior."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from store.json_store import JsonStore
from dal.dalmain import DataAccessLayer


@pytest.fixture()
def mock_data_path():
    """
    Create a temp copy of mock_data.json so tests don't mutate
    the real file.  Yields the temp path, cleans up after.
    """
    src = Path(__file__).resolve().parent.parent / "mock_data.json"
    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", delete=False,
    )
    shutil.copy(src, tmp.name)
    tmp.close()
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture()
def client(mock_data_path):
    """
    FastAPI TestClient wired to a DAL backed by the temp JSON.
    """
    store = JsonStore(path=mock_data_path)
    dal = DataAccessLayer.from_json(store=store)
    app.state.dal = dal
    return TestClient(app)


def _first_enrollment(mock_data_path: str) -> dict:
    """Return the first enrollment from the mock data."""
    raw = json.loads(Path(mock_data_path).read_text())
    return raw["Enrollment"][0]


def _find_video_lesson(mock_data_path: str) -> dict | None:
    """Return a VideoLesson that belongs to a course with enrollments."""
    raw = json.loads(Path(mock_data_path).read_text())
    enrolled_courses = {e["course_id"] for e in raw["Enrollment"]}
    for lesson in raw["Lessons"]:
        if (
            lesson["lesson_type"] == "VideoLesson"
            and lesson["course_id"] in enrolled_courses
        ):
            return lesson
    return None


def _find_article_lesson(mock_data_path: str) -> dict | None:
    """Return an ArticleLesson from an enrolled course."""
    raw = json.loads(Path(mock_data_path).read_text())
    enrolled_courses = {e["course_id"] for e in raw["Enrollment"]}
    for lesson in raw["Lessons"]:
        if (
            lesson["lesson_type"] == "ArticleLesson"
            and lesson["course_id"] in enrolled_courses
        ):
            return lesson
    return None


def _find_quiz_lesson(mock_data_path: str) -> dict | None:
    """Return a QuizLesson from an enrolled course."""
    raw = json.loads(Path(mock_data_path).read_text())
    enrolled_courses = {e["course_id"] for e in raw["Enrollment"]}
    for lesson in raw["Lessons"]:
        if (
            lesson["lesson_type"] == "QuizLesson"
            and lesson["course_id"] in enrolled_courses
        ):
            return lesson
    return None


class TestUpsertLessonProgress:

    def test_create_video_progress(
        self, client, mock_data_path,
    ):
        lesson = _find_video_lesson(mock_data_path)
        if lesson is None:
            pytest.skip("No VideoLesson in enrolled course")

        enroll = _first_enrollment(mock_data_path)
        resp = client.post("/progress/lesson", json={
            "user_id": enroll["user_id"],
            "course_id": lesson["course_id"],
            "module_id": lesson["module_id"],
            "lesson_id": lesson["_id"],
            "time_spent": lesson["meta_data"].get("duration", 100) / 2,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["progress_percent"] == 50.0

    def test_upsert_updates_existing(
        self, client, mock_data_path,
    ):
        lesson = _find_video_lesson(mock_data_path)
        if lesson is None:
            pytest.skip("No VideoLesson in enrolled course")

        enroll = _first_enrollment(mock_data_path)
        duration = lesson["meta_data"].get("duration", 100)
        payload = {
            "user_id": enroll["user_id"],
            "course_id": lesson["course_id"],
            "module_id": lesson["module_id"],
            "lesson_id": lesson["_id"],
            "time_spent": duration / 2,
        }

        first = client.post("/progress/lesson", json=payload)
        assert first.status_code == 200
        assert first.json()["status"] == "in_progress"

        payload["time_spent"] = duration
        second = client.post("/progress/lesson", json=payload)
        assert second.status_code == 200
        assert second.json()["status"] == "completed"
        assert second.json()["progress_percent"] == 100.0
        assert second.json()["_id"] == first.json()["_id"]

    def test_create_article_progress(
        self, client, mock_data_path,
    ):
        lesson = _find_article_lesson(mock_data_path)
        if lesson is None:
            pytest.skip("No ArticleLesson in enrolled course")

        enroll = _first_enrollment(mock_data_path)
        resp = client.post("/progress/lesson", json={
            "user_id": enroll["user_id"],
            "course_id": lesson["course_id"],
            "module_id": lesson["module_id"],
            "lesson_id": lesson["_id"],
            "progress_percent": 75.0,
        })

        assert resp.status_code == 200
        assert resp.json()["progress_percent"] == 75.0
        assert resp.json()["status"] == "in_progress"

    def test_create_quiz_progress_completed(
        self, client, mock_data_path,
    ):
        lesson = _find_quiz_lesson(mock_data_path)
        if lesson is None:
            pytest.skip("No QuizLesson in enrolled course")

        enroll = _first_enrollment(mock_data_path)
        resp = client.post("/progress/lesson", json={
            "user_id": enroll["user_id"],
            "course_id": lesson["course_id"],
            "module_id": lesson["module_id"],
            "lesson_id": lesson["_id"],
            "is_completed": True,
        })

        assert resp.status_code == 200
        assert resp.json()["progress_percent"] == 100.0
        assert resp.json()["status"] == "completed"

    def test_missing_required_field_returns_422(
        self, client, mock_data_path,
    ):
        lesson = _find_video_lesson(mock_data_path)
        if lesson is None:
            pytest.skip("No VideoLesson in enrolled course")

        enroll = _first_enrollment(mock_data_path)
        resp = client.post("/progress/lesson", json={
            "user_id": enroll["user_id"],
            "course_id": lesson["course_id"],
            "module_id": lesson["module_id"],
            "lesson_id": lesson["_id"],
        })

        assert resp.status_code == 422

    def test_not_enrolled_returns_404(self, client):
        resp = client.post("/progress/lesson", json={
            "user_id": "nonexistent_user",
            "course_id": "nonexistent_course",
            "module_id": "mod_1",
            "lesson_id": "lesson_1",
            "time_spent": 10,
        })

        assert resp.status_code == 404

    def test_lesson_not_found_returns_404(
        self, client, mock_data_path,
    ):
        enroll = _first_enrollment(mock_data_path)
        resp = client.post("/progress/lesson", json={
            "user_id": enroll["user_id"],
            "course_id": enroll["course_id"],
            "module_id": "mod_1",
            "lesson_id": "nonexistent_lesson",
            "time_spent": 10,
        })

        assert resp.status_code == 404


class TestCascadeOnCompletion:

    def test_no_cascade_on_partial_progress(
        self, client, mock_data_path,
    ):
        lesson = _find_video_lesson(mock_data_path)
        if lesson is None:
            pytest.skip("No VideoLesson in enrolled course")

        enroll = _first_enrollment(mock_data_path)
        duration = lesson["meta_data"].get("duration", 100)

        before = client.get(
            f"/progress/module/{enroll['user_id']}"
            f"/{lesson['course_id']}",
        ).json()

        client.post("/progress/lesson", json={
            "user_id": enroll["user_id"],
            "course_id": lesson["course_id"],
            "module_id": lesson["module_id"],
            "lesson_id": lesson["_id"],
            "time_spent": duration / 4,
        })

        after = client.get(
            f"/progress/module/{enroll['user_id']}"
            f"/{lesson['course_id']}",
        ).json()

        assert before == after

    def test_cascade_triggers_on_completion(
        self, client, mock_data_path,
    ):
        lesson = _find_video_lesson(mock_data_path)
        if lesson is None:
            pytest.skip("No VideoLesson in enrolled course")

        enroll = _first_enrollment(mock_data_path)
        duration = lesson["meta_data"].get("duration", 100)

        client.post("/progress/lesson", json={
            "user_id": enroll["user_id"],
            "course_id": lesson["course_id"],
            "module_id": lesson["module_id"],
            "lesson_id": lesson["_id"],
            "time_spent": duration,
        })

        modules = client.get(
            f"/progress/module/{enroll['user_id']}"
            f"/{lesson['course_id']}",
        )
        module_records = modules.json()
        matching = [
            mp for mp in module_records
            if mp["module_id"] == lesson["module_id"]
        ]
        assert len(matching) == 1
        assert matching[0]["completed_lessons"] >= 1
