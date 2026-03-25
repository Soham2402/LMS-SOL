from __future__ import annotations

from typing import Optional

from ..dal.abstractdal import (
    IEnrollmentRepository,
    ILessonProgressRepository,
    IModuleProgressRepository,
)
from ..models import Enrollment, LessonProgress, ModuleProgress
from ..store.json_store import JsonStore


class JsonEnrollmentRepository(IEnrollmentRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_id(self, enrollment_id: str) -> Optional[Enrollment]:
        return self._store.enrollments_by_id.get(enrollment_id)

    def get_by_user_and_course(
        self, user_id: str, course_id: str
    ) -> Optional[Enrollment]:
        user_enrollments = self._store.enrollments_by_user_id.get(user_id, [])
        return next((e for e in user_enrollments if e.course_id == course_id), None)

    def list_by_user(self, user_id: str) -> list[Enrollment]:
        return self._store.enrollments_by_user_id.get(user_id, [])

    def list_by_course(self, course_id: str) -> list[Enrollment]:
        return self._store.enrollments_by_course_id.get(course_id, [])


class JsonLessonProgressRepository(ILessonProgressRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_id(self, progress_id: str) -> Optional[LessonProgress]:
        return self._store.lesson_progress_by_id.get(progress_id)

    def get_by_user_and_lesson(
        self, user_id: str, lesson_id: str
    ) -> Optional[LessonProgress]:
        return self._store.lesson_progress_by_user_lesson.get((user_id, lesson_id))

    def list_by_user_and_course(
        self, user_id: str, course_id: str
    ) -> list[LessonProgress]:
        return self._store.lesson_progress_by_user_course.get((user_id, course_id), [])

    def list_by_user_and_module(
        self, user_id: str, module_id: str
    ) -> list[LessonProgress]:
        return self._store.lesson_progress_by_user_module.get((user_id, module_id), [])


class JsonModuleProgressRepository(IModuleProgressRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_id(self, progress_id: str) -> Optional[ModuleProgress]:
        return self._store.module_progress_by_id.get(progress_id)

    def get_by_user_and_module(
        self, user_id: str, module_id: str
    ) -> Optional[ModuleProgress]:
        return self._store.module_progress_by_user_module.get((user_id, module_id))

    def list_by_user_and_course(
        self, user_id: str, course_id: str
    ) -> list[ModuleProgress]:
        return self._store.module_progress_by_user_course.get((user_id, course_id), [])
