"""Tests for the progress recalculation utilities in utils.py."""

from datetime import datetime, timezone
from uuid import uuid4

from models.models import LessonProgress
from utils import (
    _determine_status,
    recalculate_course_progress,
    recalculate_module_progress,
    recalculate_progress_from_lesson,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _complete_lesson(dal, user_id, course_id, module_id, lesson_id):
    """Helper to create a completed lesson progress record."""
    now = _now_iso()
    lp = LessonProgress(
        _id=f"lp_{uuid4().hex[:8]}",
        user_id=user_id,
        course_id=course_id,
        module_id=module_id,
        lesson_id=lesson_id,
        status="completed",
        progress_percent=100.0,
        last_position=None,
        completed_at=now,
        updated_at=now,
    )
    return dal.lesson_progress.create(lp)


# -------------------------------------------------------------------
# _determine_status
# -------------------------------------------------------------------

class TestDetermineStatus:

    def test_all_completed(self):
        assert _determine_status(4, 4) == "completed"

    def test_some_completed(self):
        assert _determine_status(2, 4) == "in_progress"

    def test_one_completed(self):
        assert _determine_status(1, 10) == "in_progress"

    def test_none_completed(self):
        assert _determine_status(0, 4) == "not_started"

    def test_zero_total_zero_completed(self):
        assert _determine_status(0, 0) == "not_started"

    def test_more_completed_than_total(self):
        assert _determine_status(5, 3) == "completed"


# -------------------------------------------------------------------
# recalculate_module_progress
# -------------------------------------------------------------------

class TestRecalculateModuleProgress:

    def test_module_with_all_lessons_completed(self, dal):
        """
        module_1 has lesson_1 and lesson_2.
        Mock data already has both completed for user_1.
        Recalculation should yield 100%.
        """
        mp = recalculate_module_progress(
            dal, "user_1", "course_1", "module_1",
        )

        assert mp.completed_lessons == 2
        assert mp.total_lessons == 2
        assert mp.progress_percent == 100.0
        assert mp.status == "completed"

    def test_module_with_no_completed_lessons(self, dal):
        """
        module_2 has 3 lessons. lesson_3 is in_progress, the
        other two have no progress at all. Zero completed.
        """
        mp = recalculate_module_progress(
            dal, "user_1", "course_1", "module_2",
        )

        assert mp.completed_lessons == 0
        assert mp.total_lessons == 3
        assert mp.progress_percent == 0.0
        assert mp.status == "not_started"

    def test_module_with_partial_completion(self, dal):
        """
        Complete one lesson in module_2 (3 total),
        then recalculate. Should be 1/3 ≈ 33.33%.
        """
        _complete_lesson(
            dal, "user_1", "course_1", "module_2", "lesson_4",
        )

        mp = recalculate_module_progress(
            dal, "user_1", "course_1", "module_2",
        )

        assert mp.completed_lessons == 1
        assert mp.total_lessons == 3
        assert mp.progress_percent == 33.33
        assert mp.status == "in_progress"

    def test_creates_new_module_progress_if_none_exists(
        self, dal,
    ):
        """
        user_2 (instructor) has no module progress.
        Enroll them first, then complete a lesson and
        verify a new module progress is created.
        """
        from models.models import Enrollment

        enrollment = Enrollment(
            _id="enroll_test",
            user_id="user_2",
            course_id="course_1",
            enrolled_at=_now_iso(),
            status="active",
            progress_percent=0.0,
            completed_lessons=0,
            total_lessons=5,
            last_accessed_at=_now_iso(),
            current_lesson_id=None,
        )
        dal.enrollments.create(enrollment)

        _complete_lesson(
            dal, "user_2", "course_1", "module_1", "lesson_1",
        )

        mp = recalculate_module_progress(
            dal, "user_2", "course_1", "module_1",
        )

        assert mp.user_id == "user_2"
        assert mp.module_id == "module_1"
        assert mp.completed_lessons == 1
        assert mp.total_lessons == 2
        assert mp.progress_percent == 50.0

    def test_updates_existing_module_progress(self, dal):
        """
        module_1 already has a module progress record (mp_1).
        Recalculating should update it in place, keeping the
        same _id.
        """
        original = dal.module_progress.get_by_user_and_module(
            "user_1", "module_1",
        )
        original_id = original._id

        mp = recalculate_module_progress(
            dal, "user_1", "course_1", "module_1",
        )

        assert mp._id == original_id


# -------------------------------------------------------------------
# recalculate_course_progress
# -------------------------------------------------------------------

class TestRecalculateCourseProgress:

    def test_updates_enrollment_completed_count(self, dal):
        """
        user_1 has 2 completed lessons out of 5 total in
        course_1. Enrollment should reflect 2/5 = 40%.
        """
        recalculate_course_progress(
            dal, "user_1", "course_1",
        )

        enrollment = dal.enrollments.get_by_user_and_course(
            "user_1", "course_1",
        )

        assert enrollment.completed_lessons == 2
        assert enrollment.progress_percent == 40.0

    def test_enrollment_marked_completed_when_all_done(
        self, dal,
    ):
        """
        Complete all remaining lessons for user_1 in course_1,
        then recalculate. Enrollment should be 'completed'.
        """
        _complete_lesson(
            dal, "user_1", "course_1", "module_2", "lesson_3",
        )
        _complete_lesson(
            dal, "user_1", "course_1", "module_2", "lesson_4",
        )
        _complete_lesson(
            dal, "user_1", "course_1", "module_2", "lesson_5",
        )

        recalculate_course_progress(
            dal, "user_1", "course_1",
        )

        enrollment = dal.enrollments.get_by_user_and_course(
            "user_1", "course_1",
        )

        assert enrollment.completed_lessons == 5
        assert enrollment.progress_percent == 100.0
        assert enrollment.status == "completed"

    def test_no_op_for_missing_course(self, dal):
        recalculate_course_progress(
            dal, "user_1", "nonexistent_course",
        )

    def test_no_op_for_missing_enrollment(self, dal):
        recalculate_course_progress(
            dal, "nonexistent_user", "course_1",
        )

    def test_enrollment_stays_active_on_partial(self, dal):
        """
        With only 2 out of 5 lessons completed the enrollment
        should remain 'active'.
        """
        recalculate_course_progress(
            dal, "user_1", "course_1",
        )

        enrollment = dal.enrollments.get_by_user_and_course(
            "user_1", "course_1",
        )

        assert enrollment.status == "active"


# -------------------------------------------------------------------
# recalculate_progress_from_lesson (full cascade)
# -------------------------------------------------------------------

class TestRecalculateProgressFromLesson:

    def test_full_cascade_updates_module_and_enrollment(
        self, dal,
    ):
        """
        Complete lesson_4 in module_2, then run the full
        cascade. Both module_2 progress and the enrollment
        should update.
        """
        _complete_lesson(
            dal, "user_1", "course_1", "module_2", "lesson_4",
        )

        mp = recalculate_progress_from_lesson(
            dal, "user_1", "course_1", "module_2",
        )

        assert mp.completed_lessons == 1
        assert mp.total_lessons == 3
        assert mp.progress_percent == 33.33
        assert mp.status == "in_progress"

        enrollment = dal.enrollments.get_by_user_and_course(
            "user_1", "course_1",
        )
        assert enrollment.completed_lessons == 3
        assert enrollment.progress_percent == 60.0

    def test_cascade_completes_entire_course(self, dal):
        """
        Complete all 3 remaining lessons in module_2.
        After cascade, both module and enrollment should
        show 100% / completed.
        """
        for lid in ("lesson_3", "lesson_4", "lesson_5"):
            _complete_lesson(
                dal, "user_1", "course_1", "module_2", lid,
            )

        mp = recalculate_progress_from_lesson(
            dal, "user_1", "course_1", "module_2",
        )

        assert mp.completed_lessons == 3
        assert mp.total_lessons == 3
        assert mp.progress_percent == 100.0
        assert mp.status == "completed"

        enrollment = dal.enrollments.get_by_user_and_course(
            "user_1", "course_1",
        )
        assert enrollment.completed_lessons == 5
        assert enrollment.progress_percent == 100.0
        assert enrollment.status == "completed"

    def test_cascade_returns_module_progress(self, dal):
        mp = recalculate_progress_from_lesson(
            dal, "user_1", "course_1", "module_1",
        )

        assert mp.module_id == "module_1"
        assert mp.user_id == "user_1"
