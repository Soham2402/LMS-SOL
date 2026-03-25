import fcntl
import json
import threading
from pathlib import Path
from typing import Any

from models.models import (
    User,
    StudentProfile,
    StudentPreferences,
    InstructorProfile,
    AdminProfile,
    Course,
    Module,
    Lesson,
    Enrollment,
    LessonProgress,
    ModuleProgress,
)


def _user(d: dict[str, Any]) -> User:
    return User(**d)


def _student_profile(d: dict[str, Any]) -> StudentProfile:
    prefs = StudentPreferences(**d["preferences"])
    return StudentProfile(
        _id=d["_id"],
        user_id=d["user_id"],
        enrolled_courses=d["enrolled_courses"],
        completed_courses=d["completed_courses"],
        preferences=prefs,
    )


def _instructor_profile(d: dict[str, Any]) -> InstructorProfile:
    return InstructorProfile(**d)


def _admin_profile(d: dict[str, Any]) -> AdminProfile:
    return AdminProfile(**d)


def _course(d: dict[str, Any]) -> Course:
    return Course(**d)


def _module(d: dict[str, Any]) -> Module:
    return Module(**d)


def _lesson(d: dict[str, Any]) -> Lesson:
    return Lesson(**d)


def _enrollment(d: dict[str, Any]) -> Enrollment:
    return Enrollment(**d)


def _lesson_progress(d: dict[str, Any]) -> LessonProgress:
    return LessonProgress(**d)


def _module_progress(d: dict[str, Any]) -> ModuleProgress:
    return ModuleProgress(**d)



class JsonStore:
    """
    Single source of truth for the in-memory data.

    Attributes are plain dicts indexed by primary key (_id)
    or by common foreign-key lookups, so every repository
    operation is an O(1) or O(n-results) lookup.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        raw = json.loads(self._path.read_text())
        self._build_indexes(raw)

    def _build_indexes(self, raw: dict[str, Any]) -> None:

        # Users
        self.users_by_id: dict[str, User] = {u["_id"]: _user(u) for u in raw["Users"]}
        self.users_by_email: dict[str, User] = {
            u.email: u for u in self.users_by_id.values()
        }
        self.users_by_username: dict[str, User] = {
            u.username: u for u in self.users_by_id.values()
        }

        # Student profiles
        self.student_profiles_by_user_id: dict[str, StudentProfile] = {
            p["user_id"]: _student_profile(p) for p in raw["StudentProfile"]
        }

        # Instructor profiles
        self.instructor_profiles_by_user_id: dict[str, InstructorProfile] = {
            p["user_id"]: _instructor_profile(p) for p in raw["InstructorProfile"]
        }

        # Admin profiles
        self.admin_profiles_by_user_id: dict[str, AdminProfile] = {
            p["user_id"]: _admin_profile(p) for p in raw["AdminProfile"]
        }

        # Courses
        self.courses_by_id: dict[str, Course] = {
            c["_id"]: _course(c) for c in raw["Courses"]
        }

        # Modules — indexed by id and by course_id for list queries
        self.modules_by_id: dict[str, Module] = {
            m["_id"]: _module(m) for m in raw["Modules"]
        }
        self.modules_by_course_id: dict[str, list[Module]] = {}
        for module in self.modules_by_id.values():
            self.modules_by_course_id.setdefault(module.course_id, []).append(module)

        # Lessons — indexed by id, module_id, and course_id
        self.lessons_by_id: dict[str, Lesson] = {
            l["_id"]: _lesson(l) for l in raw["Lessons"]
        }
        self.lessons_by_module_id: dict[str, list[Lesson]] = {}
        self.lessons_by_course_id: dict[str, list[Lesson]] = {}
        for lesson in self.lessons_by_id.values():
            self.lessons_by_module_id.setdefault(lesson.module_id, []).append(lesson)
            self.lessons_by_course_id.setdefault(lesson.course_id, []).append(lesson)

        # Enrollments — indexed by id, user_id, and course_id
        self.enrollments_by_id: dict[str, Enrollment] = {
            e["_id"]: _enrollment(e) for e in raw["Enrollment"]
        }
        self.enrollments_by_user_id: dict[str, list[Enrollment]] = {}
        self.enrollments_by_course_id: dict[str, list[Enrollment]] = {}
        for enroll in self.enrollments_by_id.values():
            self.enrollments_by_user_id.setdefault(enroll.user_id, []).append(enroll)
            self.enrollments_by_course_id.setdefault(enroll.course_id, []).append(
                enroll
            )

        # Lesson progress — indexed by id, (user_id, lesson_id), user+course, user+module
        self.lesson_progress_by_id: dict[str, LessonProgress] = {
            lp["_id"]: _lesson_progress(lp) for lp in raw["LessonProgress"]
        }
        self.lesson_progress_by_user_lesson: dict[tuple[str, str], LessonProgress] = {
            (lp.user_id, lp.lesson_id): lp for lp in self.lesson_progress_by_id.values()
        }
        self.lesson_progress_by_user_course: dict[
            tuple[str, str], list[LessonProgress]
        ] = {}
        self.lesson_progress_by_user_module: dict[
            tuple[str, str], list[LessonProgress]
        ] = {}
        for lp in self.lesson_progress_by_id.values():
            self.lesson_progress_by_user_course.setdefault(
                (lp.user_id, lp.course_id), []
            ).append(lp)
            self.lesson_progress_by_user_module.setdefault(
                (lp.user_id, lp.module_id), []
            ).append(lp)

        # Module progress — indexed by id, (user_id, module_id), user+course
        self.module_progress_by_id: dict[str, ModuleProgress] = {
            mp["_id"]: _module_progress(mp) for mp in raw["ModuleProgress"]
        }
        self.module_progress_by_user_module: dict[tuple[str, str], ModuleProgress] = {
            (mp.user_id, mp.module_id): mp for mp in self.module_progress_by_id.values()
        }
        self.module_progress_by_user_course: dict[
            tuple[str, str], list[ModuleProgress]
        ] = {}
        for mp in self.module_progress_by_id.values():
            self.module_progress_by_user_course.setdefault(
                (mp.user_id, mp.course_id), []
            ).append(mp)

    def _add_record(self, collection_key: str, data: dict[str, Any]) -> None:
        """
        Persist a new record to the JSON file and rebuild all indexes.

        Acquires an in-process threading lock and an OS-level exclusive file
        lock so concurrent requests and processes don't corrupt the file or
        leave indexes in a half-built state.
        """
        with self._lock:
            with open(self._path, "r+") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    raw = json.load(f)
                    raw[collection_key].append(data)
                    f.seek(0)
                    f.truncate()
                    json.dump(raw, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            self._build_indexes(raw)

    def _update_record(self, collection_key: str, data: dict[str, Any]) -> None:
        """
        Update an existing record in the JSON file by matching _id, then rebuild indexes.

        Same locking strategy as _add_record.
        """
        with self._lock:
            with open(self._path, "r+") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    raw = json.load(f)
                    records = raw[collection_key]
                    for i, record in enumerate(records):
                        if record["_id"] == data["_id"]:
                            records[i] = data
                            break
                    f.seek(0)
                    f.truncate()
                    json.dump(raw, f, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            self._build_indexes(raw)

    def add_enrollment(self, data: dict[str, Any]) -> Enrollment:
        """Persist a new enrollment and return the indexed dataclass."""
        self._add_record("Enrollment", data)
        return self.enrollments_by_id[data["_id"]]

    def add_lesson_progress(self, data: dict[str, Any]) -> LessonProgress:
        """Persist a new lesson progress record and return the indexed dataclass."""
        self._add_record("LessonProgress", data)
        return self.lesson_progress_by_id[data["_id"]]

    def add_module_progress(self, data: dict[str, Any]) -> ModuleProgress:
        """Persist a new module progress record and return the indexed dataclass."""
        self._add_record("ModuleProgress", data)
        return self.module_progress_by_id[data["_id"]]

    def update_lesson_progress(self, data: dict[str, Any]) -> LessonProgress:
        """Update an existing lesson progress record and return the indexed dataclass."""
        self._update_record("LessonProgress", data)
        return self.lesson_progress_by_id[data["_id"]]

    def update_enrollment(self, data: dict[str, Any]) -> Enrollment:
        """Update an existing enrollment record and return the indexed dataclass."""
        self._update_record("Enrollment", data)
        return self.enrollments_by_id[data["_id"]]

    def update_module_progress(self, data: dict[str, Any]) -> ModuleProgress:
        """Update an existing module progress record and return the indexed dataclass."""
        self._update_record("ModuleProgress", data)
        return self.module_progress_by_id[data["_id"]]
