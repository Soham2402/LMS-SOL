# LMS — Learning Management System
### Please read CleanThoughtProcess.md for my entire thought process and Roughplan.md for my thinking path
A Udemy-style backend built with **FastAPI** and a JSON-file data store, focused on
clean abstractions (repository-pattern DAL) and extensible progress tracking
(strategy-pattern calculators per lesson type).

---

## Prerequisites

| Tool   | Version    | Why                                   |
|--------|------------|---------------------------------------|
| Python | >= 3.14    | Required by `pyproject.toml`          |
| uv     | any recent | Fast Python package & project manager |

### Installing uv

```bash
# Linux / macOS — recommended one-liner
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip if you prefer
pip install uv
```

After install, confirm it works:

```bash
uv --version
```

---

## Project Setup

```bash
# 1. Clone the repo and cd into it
git clone <repo-url>
cd LMS

# 2. Let uv create the virtualenv and install all deps (including dev deps)
uv sync

# That's it — uv reads pyproject.toml, resolves deps, and installs into .venv/
```

---

## Running the Server

```bash
uv run uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive docs at `http://127.0.0.1:8000/docs`.

---

## Running Tests

```bash
# Run the full suite (56 tests) with verbose output
uv run pytest tests/ -v

# Run a single test file
uv run pytest tests/test_enrollment.py -v

# Run a single test class
uv run pytest tests/test_progress_calculators.py::TestVideoProgressCalculator -v

# Run a single test by name
uv run pytest tests/test_enrollment.py::TestCreateEnrollment::test_enroll_user_in_course -v
```

---

## Test Documentation

The test suite lives in `tests/` and covers four areas: enrollment endpoints,
lesson-progress endpoints (including the cascade side-effects), the
strategy-pattern progress calculators, and the utility functions that
recalculate progress up the lesson → module → course chain.

Every test works against a **temporary copy** of `mock_data.json` so the real
data file is never mutated. The fixtures that wire this up live in `conftest.py`.

### `tests/conftest.py` — Shared Fixtures

| Fixture / Helper    | What it provides |
|---------------------|------------------|
| `mock_data_path`    | Copies `mock_data.json` to a temp file before each test and deletes it after. Every write-test gets its own isolated snapshot of the data. |
| `client`            | A FastAPI `TestClient` wired to a `DataAccessLayer` backed by the temp JSON file. Used by endpoint-level (integration) tests. |
| `dal`               | A bare `DataAccessLayer` instance (no HTTP layer). Used by unit tests that call `utils.py` functions directly. |
| `load_raw(path)`    | Helper that reads the raw JSON dict from the temp file so tests can inspect the seed data before making assertions. |

---

### `tests/test_enrollment.py` — Enrollment Endpoints

Tests the `POST /enrollments` and `GET /enrollments/{user_id}` endpoints
through the FastAPI `TestClient`.

#### `TestCreateEnrollment` (5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_enroll_user_in_course` | Happy path — enrolls a user who isn't already enrolled. Asserts 201 status, correct `user_id`, `course_id`, initial `status="active"`, `progress_percent=0`, `completed_lessons=0`, `total_lessons` matching the course, `current_lesson_id=None`, and that the generated `_id` starts with `enroll_`. |
| `test_enrollment_sets_timestamps` | The created enrollment has non-null `enrolled_at` and `last_accessed_at`, and both are identical (set to "now" at creation time). |
| `test_user_not_found_returns_404` | Enrolling a nonexistent `user_id` returns 404 with `"User not found"`. |
| `test_course_not_found_returns_404` | Enrolling into a nonexistent `course_id` returns 404 with `"Course not found"`. |
| `test_duplicate_enrollment_returns_409` | Re-enrolling an already-enrolled user+course pair returns 409 with `"already enrolled"`. |

#### `TestListEnrollments` (4 tests)

| Test | What it verifies |
|------|-----------------|
| `test_list_enrollments_for_enrolled_user` | `GET /enrollments/{user_id}` returns 200 with a list containing at least the seed enrollment. |
| `test_list_enrollments_for_user_with_none` | A user with no enrollments gets 200 and an empty (or valid) list — not an error. |
| `test_list_enrollments_user_not_found_returns_404` | Requesting enrollments for a nonexistent user returns 404. |
| `test_new_enrollment_appears_in_list` | After creating an enrollment via POST, a subsequent GET for that user includes the new `course_id` in the list. Verifies write-through to the in-memory index. |

---

### `tests/test_lesson_progress_endpoint.py` — Lesson Progress Upsert & Cascade

Tests `POST /progress/lesson` (upsert semantics) and the cascade behavior that
triggers when a lesson is completed.

Two local helpers build test data:
- `_first_enrollment(path)` — returns the first enrollment from mock data.
- `_find_lesson_by_type(path, type)` — finds a lesson of a given type
  (`VideoLesson`, `ArticleLesson`, `QuizLesson`) that belongs to an enrolled
  course.

#### `TestUpsertLessonProgress` (7 tests)

| Test | What it verifies |
|------|-----------------|
| `test_create_video_progress` | Posting with `time_spent = duration / 2` for a `VideoLesson` returns `progress_percent=50.0` and `status="in_progress"`. Confirms the video calculator is invoked correctly through the endpoint. |
| `test_upsert_updates_existing` | Sending progress for the same lesson twice doesn't create a duplicate — the second call updates the existing record (same `_id`). First call at 50% is `in_progress`; second call at full duration is `completed` at 100%. |
| `test_create_article_progress` | Posting `progress_percent=75.0` for an `ArticleLesson` stores that value and sets `status="in_progress"`. |
| `test_create_quiz_progress_completed` | Posting `is_completed=True` for a `QuizLesson` returns 100% and `"completed"`. |
| `test_missing_required_field_returns_422` | Posting a `VideoLesson` without `time_spent` (the field the video calculator requires) returns 422, proving the calculator's validation bubbles up as an HTTP error. |
| `test_not_enrolled_returns_404` | Posting progress for a user+course pair with no enrollment returns 404. |
| `test_lesson_not_found_returns_404` | Posting progress for a nonexistent `lesson_id` returns 404. |

#### `TestCascadeOnCompletion` (2 tests)

These test the side-effect: when a lesson is completed, the endpoint triggers
`recalculate_progress_from_lesson` which cascades module → course progress.

| Test | What it verifies |
|------|-----------------|
| `test_no_cascade_on_partial_progress` | Submitting partial progress (`time_spent = duration / 4`, so `status="in_progress"`) does **not** trigger a cascade. Module progress before and after the call is identical. |
| `test_cascade_triggers_on_completion` | Completing a lesson (`time_spent = duration`) triggers the cascade. After the call, `GET /progress/module/{user}/{course}` shows a module progress record for that module with `completed_lessons >= 1`. |

---

### `tests/test_progress_calculators.py` — Strategy-Pattern Calculators

Pure unit tests for `progress_calculators.py`. No HTTP, no DAL — these
instantiate calculators directly with a minimal `Lesson` dataclass built by the
`_make_lesson` helper.

#### `TestVideoProgressCalculator` (7 tests)

| Test | What it verifies |
|------|-----------------|
| `test_partial_progress` | 30s watched out of 100s duration → 30%, `"in_progress"`. |
| `test_full_completion` | 200s watched out of 200s → 100%, `"completed"`. |
| `test_caps_at_100` | 999s watched out of 50s → still 100% (clamped), `"completed"`. |
| `test_zero_time_spent` | 0s watched → 0%, `"not_started"`. |
| `test_missing_time_spent_raises` | Calling without `time_spent` raises `ValueError` matching `"time_spent"`. |
| `test_missing_duration_raises` | Lesson with empty `meta_data` (no `duration` key) raises `ValueError` matching `"duration"`. |
| `test_zero_duration_raises` | Lesson with `duration=0` raises `ValueError` (avoids division by zero). |

#### `TestArticleProgressCalculator` (5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_partial_progress` | 45% input → 45%, `"in_progress"`. |
| `test_full_completion` | 100% input → 100%, `"completed"`. |
| `test_clamps_above_100` | 150% input → clamped to 100%, `"completed"`. |
| `test_clamps_below_0` | -10% input → clamped to 0%, `"not_started"`. |
| `test_missing_progress_percent_raises` | Calling without `progress_percent` raises `ValueError`. |

#### `TestQuizProgressCalculator` (3 tests)

| Test | What it verifies |
|------|-----------------|
| `test_completed` | `is_completed=True` → 100%, `"completed"`. |
| `test_not_completed` | `is_completed=False` → 0%, `"not_started"`. |
| `test_missing_is_completed_raises` | Calling without `is_completed` raises `ValueError`. |

#### `TestGetCalculator` (4 tests)

| Test | What it verifies |
|------|-----------------|
| `test_returns_video_calculator` | `get_calculator("VideoLesson")` returns a `VideoProgressCalculator` instance. |
| `test_returns_article_calculator` | `get_calculator("ArticleLesson")` returns an `ArticleProgressCalculator` instance. |
| `test_returns_quiz_calculator` | `get_calculator("QuizLesson")` returns a `QuizProgressCalculator` instance. |
| `test_unknown_type_raises` | `get_calculator("UnknownLesson")` raises `ValueError` with `"No calculator"`. |

---

### `tests/test_progress_calculation.py` — Recalculation Utilities

Unit tests for the three recalculation functions in `utils.py` plus the
`_determine_status` helper. These use the `dal` fixture (no HTTP) and the
`_complete_lesson` helper to quickly create completed `LessonProgress` records.

#### `TestDetermineStatus` (6 tests)

| Test | What it verifies |
|------|-----------------|
| `test_all_completed` | 4 of 4 → `"completed"`. |
| `test_some_completed` | 2 of 4 → `"in_progress"`. |
| `test_one_completed` | 1 of 10 → `"in_progress"`. |
| `test_none_completed` | 0 of 4 → `"not_started"`. |
| `test_zero_total_zero_completed` | 0 of 0 → `"not_started"`. |
| `test_more_completed_than_total` | 5 of 3 (edge case) → `"completed"`. |

#### `TestRecalculateModuleProgress` (5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_module_with_all_lessons_completed` | `module_1` has lessons 1 & 2 both completed in seed data → recalculation yields `completed_lessons=2`, `total_lessons=2`, `100%`, `"completed"`. |
| `test_module_with_no_completed_lessons` | `module_2` has `lesson_3` as `in_progress` and two others untracked → recalculation yields 0 completed, 0%, `"not_started"`. |
| `test_module_with_partial_completion` | Complete one lesson in `module_2` (3 total) → 1/3 = 33.33%, `"in_progress"`. |
| `test_creates_new_module_progress_if_none_exists` | Enrolls `user_2`, completes a lesson, then recalculates. Since no module progress existed for that user, a new record is created with the correct values. |
| `test_updates_existing_module_progress` | `module_1` already has a module progress record (`mp_1`). After recalculation the `_id` remains the same, proving it was updated in place rather than duplicated. |

#### `TestRecalculateCourseProgress` (5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_updates_enrollment_completed_count` | With 2 completed lessons out of 5 total, enrollment shows `completed_lessons=2`, `progress_percent=40.0`. |
| `test_enrollment_marked_completed_when_all_done` | Completes all 3 remaining lessons then recalculates → `completed_lessons=5`, `progress_percent=100.0`, `status="completed"`. |
| `test_no_op_for_missing_course` | Calling with a nonexistent `course_id` does nothing (no crash). |
| `test_no_op_for_missing_enrollment` | Calling with a nonexistent `user_id` does nothing (no crash). |
| `test_enrollment_stays_active_on_partial` | With only 2 of 5 lessons completed the enrollment status remains `"active"`, not prematurely marked completed. |

#### `TestRecalculateProgressFromLesson` (3 tests)

These test the full cascade: lesson completion → module recalculation → course
recalculation, all in one call.

| Test | What it verifies |
|------|-----------------|
| `test_full_cascade_updates_module_and_enrollment` | Completing `lesson_4` in `module_2` then cascading: module shows 1/3 at 33.33% `"in_progress"`, and enrollment shows 3 completed at 60% (2 from seed + 1 new). |
| `test_cascade_completes_entire_course` | Completing all 3 lessons in `module_2` then cascading: module is 100% `"completed"`, enrollment is 5/5 at 100% `"completed"`. |
| `test_cascade_returns_module_progress` | The return value of the cascade function is the `ModuleProgress` record with the correct `module_id` and `user_id`. |
