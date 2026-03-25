from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal, Optional


# We can simply add new user roles and lessontypes here
# We can use pydantic dataclasses too for API validation and use them for both


UserRole = Literal["Student", "Instructor", "Admin"]
LessonType = Literal["VideoLesson", "ArticleLesson", "QuizLesson"]
ProgressStatus = Literal["not_started", "in_progress", "completed"]
EnrollStatus = Literal["active", "completed", "dropped"]


@dataclass
class User:
    _id: str
    username: str
    email: str
    hashedpassword: str
    created_on: str
    is_verified: bool
    roles: list[UserRole]
    last_login: str
    gender: str


@dataclass
class StudentPreferences:
    language: str
    autoplay: bool
    playback_speed: float


@dataclass
class StudentProfile:
    _id: str
    user_id: str
    enrolled_courses: list[str]
    completed_courses: list[str]
    preferences: StudentPreferences


@dataclass
class InstructorProfile:
    _id: str
    user_id: str
    courses_created: list[str]
    ratings: float
    total_reviews: int
    total_courses: int


@dataclass
class AdminProfile:
    _id: str
    user_id: str
    permissions: list[str]


@dataclass
class Course:
    _id: str
    author_id: str
    title: str
    description: str
    modules: list[str]
    total_lessons: int


@dataclass
class Module:
    _id: str
    course_id: str
    title: str
    description: str
    order: int
    lessons: list[str]
    total_lessons: int


@dataclass
class Lesson:
    _id: str
    module_id: str
    course_id: str
    title: str
    description: str
    order: int
    lesson_type: LessonType
    content: Optional[str]
    meta_data: dict[str, Any]


@dataclass
class Enrollment:
    _id: str
    user_id: str
    course_id: str
    enrolled_at: str
    status: EnrollStatus
    progress_percent: float
    completed_lessons: int
    total_lessons: int
    last_accessed_at: str
    current_lesson_id: Optional[str]


@dataclass
class LessonProgress:
    _id: str
    user_id: str
    course_id: str
    module_id: str
    lesson_id: str
    status: ProgressStatus
    progress_percent: float
    last_position: Optional[float]
    completed_at: Optional[str]
    updated_at: str


@dataclass
class ModuleProgress:
    _id: str
    user_id: str
    course_id: str
    module_id: str
    completed_lessons: int
    total_lessons: int
    progress_percent: float
    status: ProgressStatus
    updated_at: str
