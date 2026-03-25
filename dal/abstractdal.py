from abc import ABC, abstractmethod
from typing import List, Optional

from models.models import (
    AdminProfile, Course, Enrollment, InstructorProfile,
    Lesson, LessonProgress, Module, ModuleProgress,
    StudentProfile, User,
)

# Inherit from the respective repository and implement them


class IUserRepository(ABC):

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]: ...

    @abstractmethod
    def list_all(self) -> List[User]: ...

    @abstractmethod
    def list_by_role(self, role: str) -> List[User]: ...


class IStudentProfileRepository(ABC):

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[StudentProfile]: ...

    @abstractmethod
    def list_enrolled_course_ids(self, user_id: str) -> List[str]: ...


class IInstructorProfileRepository(ABC):

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[InstructorProfile]: ...

    @abstractmethod
    def list_course_ids(self, user_id: str) -> List[str]: ...


class IAdminProfileRepository(ABC):

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[AdminProfile]: ...

    @abstractmethod
    def has_permission(self, user_id: str, permission: str) -> bool: ...


class ICourseRepository(ABC):

    @abstractmethod
    def get_by_id(self, course_id: str) -> Optional[Course]: ...

    @abstractmethod
    def list_all(self) -> List[Course]: ...

    @abstractmethod
    def list_by_author(self, author_id: str) -> List[Course]: ...


class IModuleRepository(ABC):

    @abstractmethod
    def get_by_id(self, module_id: str) -> Optional[Module]: ...

    @abstractmethod
    def list_by_course(self, course_id: str) -> List[Module]: ...


class ILessonRepository(ABC):

    @abstractmethod
    def get_by_id(self, lesson_id: str) -> Optional[Lesson]: ...

    @abstractmethod
    def list_by_module(self, module_id: str) -> List[Lesson]: ...

    @abstractmethod
    def list_by_course(self, course_id: str) -> List[Lesson]: ...


class IEnrollmentRepository(ABC):

    @abstractmethod
    def get_by_id(self, enrollment_id: str) -> Optional[Enrollment]: ...

    @abstractmethod
    def get_by_user_and_course(self, user_id: str,
                               course_id: str) -> Optional[Enrollment]: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[Enrollment]: ...

    @abstractmethod
    def list_by_course(self, course_id: str) -> List[Enrollment]: ...

    @abstractmethod
    def create(self, enrollment: Enrollment) -> Enrollment: ...

    @abstractmethod
    def update(self, enrollment: Enrollment) -> Enrollment: ...


class ILessonProgressRepository(ABC):

    @abstractmethod
    def get_by_id(self, progress_id: str) -> Optional[LessonProgress]: ...

    @abstractmethod
    def get_by_user_and_lesson(self, user_id: str,
                               lesson_id: str) -> Optional[LessonProgress]: ...

    @abstractmethod
    def list_by_user_and_course(self, user_id: str,
                                course_id: str) -> List[LessonProgress]: ...

    @abstractmethod
    def list_by_user_and_module(self, user_id: str,
                                module_id: str) -> List[LessonProgress]: ...

    @abstractmethod
    def create(self, progress: LessonProgress) -> LessonProgress: ...

    @abstractmethod
    def update(self, progress: LessonProgress) -> LessonProgress: ...


class IModuleProgressRepository(ABC):

    @abstractmethod
    def get_by_id(self, progress_id: str) -> Optional[ModuleProgress]: ...

    @abstractmethod
    def get_by_user_and_module(self, user_id: str,
                               module_id: str) -> Optional[ModuleProgress]: ...

    @abstractmethod
    def list_by_user_and_course(self, user_id: str,
                                course_id: str) -> List[ModuleProgress]: ...

    @abstractmethod
    def create(self, progress: ModuleProgress) -> ModuleProgress: ...

    @abstractmethod
    def update(self, progress: ModuleProgress) -> ModuleProgress: ...
