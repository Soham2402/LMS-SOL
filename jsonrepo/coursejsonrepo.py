from __future__ import annotations

from typing import Optional

from dal.abstractdal import (
    ICourseRepository, ILessonRepository, IModuleRepository,
)
from models.models import Course, Lesson, Module
from store.json_store import JsonStore


class JsonCourseRepository(ICourseRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_id(self, course_id: str) -> Optional[Course]:
        return self._store.courses_by_id.get(course_id)

    def list_all(self) -> list[Course]:
        return list(self._store.courses_by_id.values())

    def list_by_author(self, author_id: str) -> list[Course]:
        return [c for c in self._store.courses_by_id.values() if c.author_id == author_id]


class JsonModuleRepository(IModuleRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_id(self, module_id: str) -> Optional[Module]:
        return self._store.modules_by_id.get(module_id)

    def list_by_course(self, course_id: str) -> list[Module]:
        modules = self._store.modules_by_course_id.get(course_id, [])
        return sorted(modules, key=lambda m: m.order)


class JsonLessonRepository(ILessonRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_id(self, lesson_id: str) -> Optional[Lesson]:
        return self._store.lessons_by_id.get(lesson_id)

    def list_by_module(self, module_id: str) -> list[Lesson]:
        lessons = self._store.lessons_by_module_id.get(module_id, [])
        return sorted(lessons, key=lambda l: l.order)

    def list_by_course(self, course_id: str) -> list[Lesson]:
        lessons = self._store.lessons_by_course_id.get(course_id, [])
        return sorted(lessons, key=lambda l: (l.module_id, l.order))