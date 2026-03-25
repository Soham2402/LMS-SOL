"""
Strategy-pattern calculators for per-lesson-type progress.

Each calculator converts type-specific input (time_spent, progress_percent,
is_completed) into a uniform (progress_percent, status) tuple. To add a new
lesson type, create a subclass and register it in _CALCULATORS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.models import Lesson


class LessonProgressCalculator(ABC):
    """
    Base class for lesson progress calculators.

    Subclasses implement `calculate` to derive progress_percent and status
    from the lesson metadata and type-specific request fields.
    """

    @abstractmethod
    def calculate(self, lesson: Lesson, **kwargs) -> tuple[float, str]:
        """
        Calculate progress percent and status for a lesson.

        Args:
            lesson: The lesson being tracked.
            **kwargs: Type-specific inputs from the request body.

        Returns:
            A tuple of (progress_percent, status).
        """
        ...


class VideoProgressCalculator(LessonProgressCalculator):
    """Calculates progress from time_spent relative to lesson duration."""

    def calculate(self, lesson: Lesson, **kwargs) -> tuple[float, str]:
        """
        Args:
            lesson: Must have meta_data["duration"] (total seconds).
            **kwargs: Expects time_spent (float, seconds watched).

        Returns:
            (progress_percent, status) based on watch time vs duration.

        Raises:
            ValueError: If time_spent is not provided or duration is missing.
        """
        time_spent = kwargs.get("time_spent")
        if time_spent is None:
            raise ValueError("time_spent is required for VideoLesson")

        duration = lesson.meta_data.get("duration", 0)
        if duration <= 0:
            raise ValueError(
                "Lesson meta_data must contain a positive 'duration'"
            )

        percent = min(round((time_spent / duration) * 100, 2), 100.0)
        status = _percent_to_status(percent)
        return percent, status


class ArticleProgressCalculator(LessonProgressCalculator):
    """Accepts a progress_percent value directly from the client."""

    def calculate(self, lesson: Lesson, **kwargs) -> tuple[float, str]:
        """
        Args:
            lesson: Not used, present for interface consistency.
            **kwargs: Expects progress_percent (float, 0-100).

        Returns:
            (progress_percent, status) clamped to 0-100.

        Raises:
            ValueError: If progress_percent is not provided.
        """
        progress_percent = kwargs.get("progress_percent")
        if progress_percent is None:
            raise ValueError(
                "progress_percent is required for ArticleLesson"
            )

        percent = min(max(round(progress_percent, 2), 0.0), 100.0)
        status = _percent_to_status(percent)
        return percent, status


class QuizProgressCalculator(LessonProgressCalculator):
    """Binary completion: either 0% or 100%."""

    def calculate(self, lesson: Lesson, **kwargs) -> tuple[float, str]:
        """
        Args:
            lesson: Not used, present for interface consistency.
            **kwargs: Expects is_completed (bool).

        Returns:
            (100.0, "completed") or (0.0, "not_started").

        Raises:
            ValueError: If is_completed is not provided.
        """
        is_completed = kwargs.get("is_completed")
        if is_completed is None:
            raise ValueError("is_completed is required for QuizLesson")

        if is_completed:
            return 100.0, "completed"
        return 0.0, "not_started"


def _percent_to_status(percent: float) -> str:
    if percent >= 100.0:
        return "completed"
    if percent > 0.0:
        return "in_progress"
    return "not_started"


_CALCULATORS: dict[str, LessonProgressCalculator] = {
    "VideoLesson": VideoProgressCalculator(),
    "ArticleLesson": ArticleProgressCalculator(),
    "QuizLesson": QuizProgressCalculator(),
}


def get_calculator(lesson_type: str) -> LessonProgressCalculator:
    """
    Return the calculator for the given lesson type.

    Args:
        lesson_type: One of the registered lesson type strings.

    Raises:
        ValueError: If the lesson type has no registered calculator.
    """
    calculator = _CALCULATORS.get(lesson_type)
    if calculator is None:
        raise ValueError(
            f"No calculator for lesson type: {lesson_type}"
        )
    return calculator
