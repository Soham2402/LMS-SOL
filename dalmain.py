# We use composition to build a data access layer using factory pattern
from .abstractdal import (
    IUserRepository,
    IStudentProfileRepository,
    IInstructorProfileRepository,
    IAdminProfileRepository,
    ICourseRepository,
    IModuleRepository,
    ILessonRepository,
    IEnrollmentRepository,
    ILessonProgressRepository,
    IModuleProgressRepository,
)

from jsonrepo.coursejsonrepo import (
    JsonCourseRepository,
    JsonModuleRepository,
    JsonLessonRepository,
)
from jsonrepo.progressjsonrepo import (
    JsonEnrollmentRepository,
    JsonLessonProgressRepository,
    JsonModuleProgressRepository,
)
from jsonrepo.userjsonrepo import (
    JsonUserRepository,
    JsonStudentProfileRepository,
    JsonInstructorProfileRepository,
    JsonAdminProfileRepository,
)


class DataAccessLayer:
    """
    Composed facade over all repositories.

    Constructor accepts interfaces — not concrete classes — so the DAL
    stays decoupled from any specific storage backend.
    """

    """

    Usage
    -----
        store = JsonStore("data.json")
        dal   = DataAccessLayer.from_json(store)

        user      = dal.users.get_by_id("user_1")
        courses   = dal.courses.list_all()
        enroll    = dal.enrollments.get_by_user_and_course("user_1", "course_1")
        lp_list   = dal.lesson_progress.list_by_user_and_course("user_1", "course_1")
    """

    def __init__(
        self,
        *,
        users: IUserRepository,
        student_profiles: IStudentProfileRepository,
        instructor_profiles: IInstructorProfileRepository,
        admin_profiles: IAdminProfileRepository,
        courses: ICourseRepository,
        modules: IModuleRepository,
        lessons: ILessonRepository,
        enrollments: IEnrollmentRepository,
        lesson_progress: ILessonProgressRepository,
        module_progress: IModuleProgressRepository,
    ) -> None:
        self.users = users
        self.student_profiles = student_profiles
        self.instructor_profiles = instructor_profiles
        self.admin_profiles = admin_profiles
        self.courses = courses
        self.modules = modules
        self.lessons = lessons
        self.enrollments = enrollments
        self.lesson_progress = lesson_progress
        self.module_progress = module_progress

    @classmethod
    def from_json(cls, store: JsonStore) -> "DataAccessLayer":
        """Wire up all JSON-backed repositories from a single JsonStore."""
        return cls(
            users=JsonUserRepository(store),
            student_profiles=JsonStudentProfileRepository(store),
            instructor_profiles=JsonInstructorProfileRepository(store),
            admin_profiles=JsonAdminProfileRepository(store),
            courses=JsonCourseRepository(store),
            modules=JsonModuleRepository(store),
            lessons=JsonLessonRepository(store),
            enrollments=JsonEnrollmentRepository(store),
            lesson_progress=JsonLessonProgressRepository(store),
            module_progress=JsonModuleProgressRepository(store),
        )
