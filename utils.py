from datetime import datetime, timezone
from uuid import uuid4

from dal.dalmain import DataAccessLayer
from models.models import ModuleProgress


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _get_dal(request: Request) -> DataAccessLayer:
    return request.app.state.dal


def _determine_status(completed: int, total: int) -> str:
    """Return a progress status string based on completion counts."""
    if total > 0 and completed >= total:
        return "completed"
    if completed > 0:
        return "in_progress"
    return "not_started"


def recalculate_module_progress(
    dal: DataAccessLayer,
    user_id: str,
    course_id: str,
    module_id: str,
) -> ModuleProgress:
    """
    Recalculate module progress from the user's lesson progress records.

    Counts completed lessons in the module, computes the percentage,
    and either updates the existing module progress or creates a new one.

    Args:
        dal: The data access layer instance.
        user_id: The user whose progress is being recalculated.
        course_id: The course the module belongs to.
        module_id: The module to recalculate progress for.

    Returns:
        The updated or newly created ModuleProgress record.
    """
    total_lessons = len(dal.lessons.list_by_module(module_id))
    lesson_progress_list = dal.lesson_progress.list_by_user_and_module(
        user_id, module_id,
    )
    completed = sum(
        1 for lp in lesson_progress_list if lp.status == "completed"
    )

    progress_percent = (
        round((completed / total_lessons) * 100, 2)
        if total_lessons > 0
        else 0.0
    )
    status = _determine_status(completed, total_lessons)
    now = _now_iso()

    existing = dal.module_progress.get_by_user_and_module(user_id, module_id)
    if existing:
        existing.completed_lessons = completed
        existing.total_lessons = total_lessons
        existing.progress_percent = progress_percent
        existing.status = status
        existing.updated_at = now
        return dal.module_progress.update(existing)

    new_progress = ModuleProgress(
        _id=f"mp_{uuid4().hex[:8]}",
        user_id=user_id,
        course_id=course_id,
        module_id=module_id,
        completed_lessons=completed,
        total_lessons=total_lessons,
        progress_percent=progress_percent,
        status=status,
        updated_at=now,
    )
    return dal.module_progress.create(new_progress)


def recalculate_course_progress(
    dal: DataAccessLayer,
    user_id: str,
    course_id: str,
) -> None:
    """
    Recalculate course-level progress on the enrollment record.

    Counts all completed lessons across every module in the course and
    updates the enrollment's progress_percent and completed_lessons fields.

    Args:
        dal: The data access layer instance.
        user_id: The user whose enrollment progress is being recalculated.
        course_id: The course to recalculate progress for.
    """
    course = dal.courses.get_by_id(course_id)
    if not course:
        return

    enrollment = dal.enrollments.get_by_user_and_course(user_id, course_id)
    if not enrollment:
        return

    total_lessons = course.total_lessons
    all_lp = dal.lesson_progress.list_by_user_and_course(user_id, course_id)
    completed = sum(1 for lp in all_lp if lp.status == "completed")

    progress_percent = (
        round((completed / total_lessons) * 100, 2)
        if total_lessons > 0
        else 0.0
    )

    enrollment.completed_lessons = completed
    enrollment.progress_percent = progress_percent
    enrollment.last_accessed_at = _now_iso()

    if total_lessons > 0 and completed >= total_lessons:
        enrollment.status = "completed"

    dal.enrollments.update(enrollment)


def recalculate_progress_from_lesson(
    dal: DataAccessLayer,
    user_id: str,
    course_id: str,
    module_id: str,
) -> ModuleProgress:
    """
    Full cascade: lesson → module → course.

    Call this after creating or updating a lesson progress record to
    propagate the change upward through the entire progress tree.

    Args:
        dal: The data access layer instance.
        user_id: The user whose progress changed.
        course_id: The course the lesson belongs to.
        module_id: The module the lesson belongs to.

    Returns:
        The updated or newly created ModuleProgress record.
    """
    module_progress = recalculate_module_progress(
        dal, user_id, course_id, module_id,
    )
    recalculate_course_progress(dal, user_id, course_id)
    return module_progress
