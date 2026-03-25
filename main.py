from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from dal.dalmain import DataAccessLayer
from models.models import Enrollment, LessonProgress, ModuleProgress
from store.json_store import JsonStore
from utils import recalculate_course_progress, recalculate_progress_from_lesson


class EnrollRequest(BaseModel):
    """Body for POST /enrollments."""
    user_id: str
    course_id: str


class LessonProgressRequest(BaseModel):
    """Body for POST /progress/lesson."""
    user_id: str
    course_id: str
    module_id: str
    lesson_id: str
    status: str = "not_started"
    progress_percent: float = 0.0
    last_position: float | None = None


class ModuleProgressRequest(BaseModel):
    """Body for POST /progress/module."""
    user_id: str
    course_id: str
    module_id: str
    completed_lessons: int = 0
    total_lessons: int = 0
    progress_percent: float = 0.0
    status: str = "not_started"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_dal(request: Request) -> DataAccessLayer:
    return request.app.state.dal


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup")
    store: JsonStore = JsonStore(path="./mock_data.json")
    app.state.dal = DataAccessLayer.from_json(store=store)
    yield
    print("Application shutdown")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


@app.post("/enrollments", status_code=201)
async def create_enrollment(body: EnrollRequest, request: Request):
    """Enroll a user in a course."""
    # we can do this using dependency injection too but for now let it be
    dal = _get_dal(request)

    if not dal.users.get_by_id(body.user_id):
        raise HTTPException(status_code=404, detail="User not found")

    course = dal.courses.get_by_id(body.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing = dal.enrollments.get_by_user_and_course(
        body.user_id, body.course_id,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="User already enrolled in this course",
        )

    now = _now_iso()
    enrollment = Enrollment(
        _id=f"enroll_{uuid4().hex[:8]}",
        user_id=body.user_id,
        course_id=body.course_id,
        enrolled_at=now,
        status="active",
        progress_percent=0.0,
        completed_lessons=0,
        total_lessons=course.total_lessons,
        last_accessed_at=now,
        current_lesson_id=None,
    )

    created = dal.enrollments.create(enrollment)
    return asdict(created)


@app.get("/enrollments/{user_id}")
async def list_user_enrollments(user_id: str, request: Request):
    """List all enrollments for a user."""
    dal = _get_dal(request)

    if not dal.users.get_by_id(user_id):
        raise HTTPException(status_code=404, detail="User not found")

    enrollments = dal.enrollments.list_by_user(user_id)
    return [asdict(e) for e in enrollments]


@app.post("/progress/lesson", status_code=201)
async def create_lesson_progress(
    body: LessonProgressRequest, request: Request,
):
    """Create a lesson progress record for a user."""
    dal = _get_dal(request)

    enrolled = dal.enrollments.get_by_user_and_course(
        body.user_id, body.course_id,
    )
    if not enrolled:
        raise HTTPException(
            status_code=404,
            detail="User is not enrolled in this course",
        )

    if not dal.lessons.get_by_id(body.lesson_id):
        raise HTTPException(
            status_code=404, detail="Lesson not found",
        )

    existing = dal.lesson_progress.get_by_user_and_lesson(
        body.user_id, body.lesson_id,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Lesson progress already exists",
        )

    now = _now_iso()
    completed_at = now if body.status == "completed" else None

    progress = LessonProgress(
        _id=f"lp_{uuid4().hex[:8]}",
        user_id=body.user_id,
        course_id=body.course_id,
        module_id=body.module_id,
        lesson_id=body.lesson_id,
        status=body.status,
        progress_percent=body.progress_percent,
        last_position=body.last_position,
        completed_at=completed_at,
        updated_at=now,
    )

    created = dal.lesson_progress.create(progress)

    recalculate_progress_from_lesson(
        dal, body.user_id, body.course_id, body.module_id,
    )

    return asdict(created)


@app.get("/progress/lesson/{user_id}/{course_id}")
async def list_lesson_progress(
    user_id: str, course_id: str, request: Request,
):
    """List all lesson progress records for a user in a course."""
    dal = _get_dal(request)

    enrolled = dal.enrollments.get_by_user_and_course(
        user_id, course_id,
    )
    if not enrolled:
        raise HTTPException(
            status_code=404,
            detail="User is not enrolled in this course",
        )

    progress_list = dal.lesson_progress.list_by_user_and_course(
        user_id, course_id,
    )
    return [asdict(lp) for lp in progress_list]



@app.post("/progress/module", status_code=201)
async def create_module_progress(
    body: ModuleProgressRequest, request: Request,
):
    """Create a module progress record for a user."""
    dal = _get_dal(request)

    enrolled = dal.enrollments.get_by_user_and_course(
        body.user_id, body.course_id,
    )
    if not enrolled:
        raise HTTPException(
            status_code=404,
            detail="User is not enrolled in this course",
        )

    if not dal.modules.get_by_id(body.module_id):
        raise HTTPException(
            status_code=404, detail="Module not found",
        )

    existing = dal.module_progress.get_by_user_and_module(
        body.user_id, body.module_id,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Module progress already exists",
        )

    now = _now_iso()
    progress = ModuleProgress(
        _id=f"mp_{uuid4().hex[:8]}",
        user_id=body.user_id,
        course_id=body.course_id,
        module_id=body.module_id,
        completed_lessons=body.completed_lessons,
        total_lessons=body.total_lessons,
        progress_percent=body.progress_percent,
        status=body.status,
        updated_at=now,
    )

    created = dal.module_progress.create(progress)

    recalculate_course_progress(dal, body.user_id, body.course_id)

    return asdict(created)


@app.get("/progress/module/{user_id}/{course_id}")
async def list_module_progress(
    user_id: str, course_id: str, request: Request,
):
    """List all module progress records for a user in a course."""
    dal = _get_dal(request)

    enrolled = dal.enrollments.get_by_user_and_course(
        user_id, course_id,
    )
    if not enrolled:
        raise HTTPException(
            status_code=404,
            detail="User is not enrolled in this course",
        )

    progress_list = dal.module_progress.list_by_user_and_course(
        user_id, course_id,
    )
    return [asdict(mp) for mp in progress_list]
