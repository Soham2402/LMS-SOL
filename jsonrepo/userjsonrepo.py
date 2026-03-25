from __future__ import annotations

from typing import Optional

from dal.abstractdal import (
    IAdminProfileRepository, IInstructorProfileRepository,
    IStudentProfileRepository, IUserRepository,
)
from models.models import (
    AdminProfile, InstructorProfile, StudentProfile, User,
)
from store.json_store import JsonStore


class JsonUserRepository(IUserRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._store.users_by_id.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return self._store.users_by_email.get(email)

    def get_by_username(self, username: str) -> Optional[User]:
        return self._store.users_by_username.get(username)

    def list_all(self) -> list[User]:
        return list(self._store.users_by_id.values())

    def list_by_role(self, role: str) -> list[User]:
        return [u for u in self._store.users_by_id.values() if role in u.roles]


class JsonStudentProfileRepository(IStudentProfileRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_user_id(self, user_id: str) -> Optional[StudentProfile]:
        return self._store.student_profiles_by_user_id.get(user_id)

    def list_enrolled_course_ids(self, user_id: str) -> list[str]:
        profile = self.get_by_user_id(user_id)
        return profile.enrolled_courses if profile else []


class JsonInstructorProfileRepository(IInstructorProfileRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_user_id(self, user_id: str) -> Optional[InstructorProfile]:
        return self._store.instructor_profiles_by_user_id.get(user_id)

    def list_course_ids(self, user_id: str) -> list[str]:
        profile = self.get_by_user_id(user_id)
        return profile.courses_created if profile else []


class JsonAdminProfileRepository(IAdminProfileRepository):

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get_by_user_id(self, user_id: str) -> Optional[AdminProfile]:
        return self._store.admin_profiles_by_user_id.get(user_id)

    def has_permission(self, user_id: str, permission: str) -> bool:
        profile = self.get_by_user_id(user_id)
        return permission in profile.permissions if profile else False