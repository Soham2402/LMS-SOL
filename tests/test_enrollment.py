"""Tests for the enrollment endpoints."""

from tests.conftest import load_raw


class TestCreateEnrollment:

    def test_enroll_user_in_course(self, client, mock_data_path):
        raw = load_raw(mock_data_path)
        user_id = raw["Users"][0]["_id"]
        course_id = raw["Courses"][0]["_id"]
        course_total = raw["Courses"][0]["total_lessons"]

        existing = raw["Enrollment"]
        already_enrolled = any(
            e["user_id"] == user_id and e["course_id"] == course_id
            for e in existing
        )
        if already_enrolled:
            user_id = raw["Users"][1]["_id"]

        resp = client.post("/enrollments", json={
            "user_id": user_id,
            "course_id": course_id,
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["course_id"] == course_id
        assert data["status"] == "active"
        assert data["progress_percent"] == 0.0
        assert data["completed_lessons"] == 0
        assert data["total_lessons"] == course_total
        assert data["current_lesson_id"] is None
        assert data["_id"].startswith("enroll_")

    def test_enrollment_sets_timestamps(
        self, client, mock_data_path,
    ):
        raw = load_raw(mock_data_path)
        user_id = raw["Users"][1]["_id"]
        course_id = raw["Courses"][0]["_id"]

        resp = client.post("/enrollments", json={
            "user_id": user_id,
            "course_id": course_id,
        })

        data = resp.json()
        assert data["enrolled_at"] is not None
        assert data["last_accessed_at"] is not None
        assert data["enrolled_at"] == data["last_accessed_at"]

    def test_user_not_found_returns_404(self, client):
        resp = client.post("/enrollments", json={
            "user_id": "nonexistent_user",
            "course_id": "course_1",
        })

        assert resp.status_code == 404
        assert "User not found" in resp.json()["detail"]

    def test_course_not_found_returns_404(
        self, client, mock_data_path,
    ):
        raw = load_raw(mock_data_path)
        user_id = raw["Users"][0]["_id"]

        resp = client.post("/enrollments", json={
            "user_id": user_id,
            "course_id": "nonexistent_course",
        })

        assert resp.status_code == 404
        assert "Course not found" in resp.json()["detail"]

    def test_duplicate_enrollment_returns_409(
        self, client, mock_data_path,
    ):
        raw = load_raw(mock_data_path)
        enroll = raw["Enrollment"][0]

        resp = client.post("/enrollments", json={
            "user_id": enroll["user_id"],
            "course_id": enroll["course_id"],
        })

        assert resp.status_code == 409
        assert "already enrolled" in resp.json()["detail"]


class TestListEnrollments:

    def test_list_enrollments_for_enrolled_user(
        self, client, mock_data_path,
    ):
        raw = load_raw(mock_data_path)
        enroll = raw["Enrollment"][0]

        resp = client.get(f"/enrollments/{enroll['user_id']}")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(
            e["course_id"] == enroll["course_id"]
            for e in data
        )

    def test_list_enrollments_for_user_with_none(
        self, client, mock_data_path,
    ):
        raw = load_raw(mock_data_path)
        enrolled_user_ids = {
            e["user_id"] for e in raw["Enrollment"]
        }
        unenrolled = next(
            (u for u in raw["Users"]
             if u["_id"] not in enrolled_user_ids),
            None,
        )
        if unenrolled is None:
            user_id = raw["Users"][1]["_id"]
        else:
            user_id = unenrolled["_id"]

        resp = client.get(f"/enrollments/{user_id}")

        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_enrollments_user_not_found_returns_404(
        self, client,
    ):
        resp = client.get("/enrollments/nonexistent_user")

        assert resp.status_code == 404
        assert "User not found" in resp.json()["detail"]

    def test_new_enrollment_appears_in_list(
        self, client, mock_data_path,
    ):
        raw = load_raw(mock_data_path)
        user_id = raw["Users"][1]["_id"]
        course_id = raw["Courses"][0]["_id"]

        client.post("/enrollments", json={
            "user_id": user_id,
            "course_id": course_id,
        })

        resp = client.get(f"/enrollments/{user_id}")

        assert resp.status_code == 200
        course_ids = [e["course_id"] for e in resp.json()]
        assert course_id in course_ids
