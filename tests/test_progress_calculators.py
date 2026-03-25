"""Tests for progress_calculators module."""

import pytest

from models.models import Lesson
from progress_calculators import (
    ArticleProgressCalculator,
    QuizProgressCalculator,
    VideoProgressCalculator,
    get_calculator,
)


def _make_lesson(
    lesson_type: str = "VideoLesson",
    meta_data: dict | None = None,
) -> Lesson:
    """Build a minimal Lesson for testing."""
    return Lesson(
        _id="lesson_1",
        module_id="mod_1",
        course_id="course_1",
        title="Test Lesson",
        description="desc",
        order=1,
        lesson_type=lesson_type,
        content=None,
        meta_data=meta_data or {},
    )


# -------------------------------------------------------------------
# VideoProgressCalculator
# -------------------------------------------------------------------

class TestVideoProgressCalculator:

    def setup_method(self):
        self.calc = VideoProgressCalculator()

    def test_partial_progress(self):
        lesson = _make_lesson(meta_data={"duration": 100})

        percent, status = self.calc.calculate(
            lesson, time_spent=30,
        )

        assert percent == 30.0
        assert status == "in_progress"

    def test_full_completion(self):
        lesson = _make_lesson(meta_data={"duration": 200})

        percent, status = self.calc.calculate(
            lesson, time_spent=200,
        )

        assert percent == 100.0
        assert status == "completed"

    def test_caps_at_100(self):
        lesson = _make_lesson(meta_data={"duration": 50})

        percent, status = self.calc.calculate(
            lesson, time_spent=999,
        )

        assert percent == 100.0
        assert status == "completed"

    def test_zero_time_spent(self):
        lesson = _make_lesson(meta_data={"duration": 100})

        percent, status = self.calc.calculate(
            lesson, time_spent=0,
        )

        assert percent == 0.0
        assert status == "not_started"

    def test_missing_time_spent_raises(self):
        lesson = _make_lesson(meta_data={"duration": 100})

        with pytest.raises(ValueError, match="time_spent"):
            self.calc.calculate(lesson)

    def test_missing_duration_raises(self):
        lesson = _make_lesson(meta_data={})

        with pytest.raises(ValueError, match="duration"):
            self.calc.calculate(lesson, time_spent=10)

    def test_zero_duration_raises(self):
        lesson = _make_lesson(meta_data={"duration": 0})

        with pytest.raises(ValueError, match="duration"):
            self.calc.calculate(lesson, time_spent=10)


# -------------------------------------------------------------------
# ArticleProgressCalculator
# -------------------------------------------------------------------

class TestArticleProgressCalculator:

    def setup_method(self):
        self.calc = ArticleProgressCalculator()

    def test_partial_progress(self):
        lesson = _make_lesson(lesson_type="ArticleLesson")

        percent, status = self.calc.calculate(
            lesson, progress_percent=45.0,
        )

        assert percent == 45.0
        assert status == "in_progress"

    def test_full_completion(self):
        lesson = _make_lesson(lesson_type="ArticleLesson")

        percent, status = self.calc.calculate(
            lesson, progress_percent=100.0,
        )

        assert percent == 100.0
        assert status == "completed"

    def test_clamps_above_100(self):
        lesson = _make_lesson(lesson_type="ArticleLesson")

        percent, status = self.calc.calculate(
            lesson, progress_percent=150.0,
        )

        assert percent == 100.0
        assert status == "completed"

    def test_clamps_below_0(self):
        lesson = _make_lesson(lesson_type="ArticleLesson")

        percent, status = self.calc.calculate(
            lesson, progress_percent=-10.0,
        )

        assert percent == 0.0
        assert status == "not_started"

    def test_missing_progress_percent_raises(self):
        lesson = _make_lesson(lesson_type="ArticleLesson")

        with pytest.raises(ValueError, match="progress_percent"):
            self.calc.calculate(lesson)


# -------------------------------------------------------------------
# QuizProgressCalculator
# -------------------------------------------------------------------

class TestQuizProgressCalculator:

    def setup_method(self):
        self.calc = QuizProgressCalculator()

    def test_completed(self):
        lesson = _make_lesson(lesson_type="QuizLesson")

        percent, status = self.calc.calculate(
            lesson, is_completed=True,
        )

        assert percent == 100.0
        assert status == "completed"

    def test_not_completed(self):
        lesson = _make_lesson(lesson_type="QuizLesson")

        percent, status = self.calc.calculate(
            lesson, is_completed=False,
        )

        assert percent == 0.0
        assert status == "not_started"

    def test_missing_is_completed_raises(self):
        lesson = _make_lesson(lesson_type="QuizLesson")

        with pytest.raises(ValueError, match="is_completed"):
            self.calc.calculate(lesson)


# -------------------------------------------------------------------
# get_calculator factory
# -------------------------------------------------------------------

class TestGetCalculator:

    def test_returns_video_calculator(self):
        calc = get_calculator("VideoLesson")
        assert isinstance(calc, VideoProgressCalculator)

    def test_returns_article_calculator(self):
        calc = get_calculator("ArticleLesson")
        assert isinstance(calc, ArticleProgressCalculator)

    def test_returns_quiz_calculator(self):
        calc = get_calculator("QuizLesson")
        assert isinstance(calc, QuizProgressCalculator)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="No calculator"):
            get_calculator("UnknownLesson")
