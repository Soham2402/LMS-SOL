# Project Design: Modular LMS

## 1. Vision & Core Objectives
The goal of this project is to build a highly extensible and abstracted Learning Management System. The architecture focuses on **separation of concerns**, ensuring that the business logic remains agnostic of the underlying data storage.

### Key Focus Areas:
* **Abstraction:** Using the Repository Pattern to decouple business logic from the Data Access Layer (DAL).
* **Extensibility:** Creating a flexible content system that handles various lesson types (Video, Quiz, PDF, Article).
* **Data Integrity:** Implementing file-level locking to prevent corruption during parallel requests in a JSON-based store.
* **Performance:** Implementing custom indexing within JSON to simulate real-world database lookups.

---

## 2. System Architecture & Data Access Layer (DAL)

### The Repository Pattern
To allow for easy switching between data sources (e.g., moving from a JSON flat-file to a SQL database), I have implemented a **Repository Pattern**. 
* Each database model has its own dedicated repository.
* The application interacts only with the repository interface, never the raw data source.

### JSON "Database" with Indexing
To explore the mechanics of database engines, I chose a JSON-based storage system.
* **Initialization:** Upon application startup, the system indexes the JSON data based on primary keys (e.g., `user_id`, `module_id`).
* **Concurrency:** To handle parallel requests without data corruption, I implemented file locking using `fcntl` and threading locks. This ensures that "Read/Write" operations are atomic at the file level.

---

## 3. Database Schema Design

### A. Course Structure
The hierarchy follows a strict parent-child relationship: **Course > Module > Lesson**.

* **Courses:** Contains high-level metadata, `author_id`, and a collection of Module IDs.
* **Modules:** Groups of lessons attached to a specific course.
* **Lessons:** The atomic unit of content. Uses a `meta_data` field to provide flexibility for different content types (Video URLs, PDF paths, Article text).

### B. User & Profile Management
To allow a single user to act as both a Student and an Instructor, I separated account credentials from role-specific data.

* **User Table:** Core authentication data (email, hashed password, roles list, verification status).
* **StudentProfile:** Tracks `enrolled_courses` and preferences.
* **InstructorProfile:** Tracks `courses_created`, ratings, and instructor-specific metadata.
* **AdminProfile:** Handles system-wide permissions.

### C. Enrollment & Progress Tracking
Progress is calculated dynamically based on the hierarchy of the course.

| Table | Responsibility | Key Metrics |
| :--- | :--- | :--- |
| **Enrollment** | Maps User to Course | `completed_percentage`, `last_lesson` |
| **ModuleProgress** | Tracks completion within a section | `module_completion_rate` |
| **LessonProgress** | Tracks individual item status | `status`, `last_timestamp`, `is_completed` |

To ensure new lesson type progress can be handled easily, I have implemented a factory where based on the request and leson_type the progress can be auto calculated. Adding a support for a new lesson type is as simple as extending the abstract class with the calculation logic
---

## 4. Business Logic & Extensibility

### Handling Diverse Lesson Types
The system uses a strategy-based approach to determine when a lesson is "complete." This logic is isolated at the application level to keep the DAL clean:
* **Video Lessons:** Completion is tracked via the `last_timestamp`.
* **Articles:** Completion is triggered when the user reaches the end of the content (scroll tracking).
* **Quizzes:** Completion is based on a passing score or submission.

### Automated Progress Calculations
To maintain data consistency, progress flows upward:
1.  **Lesson** is marked completed.
2.  **Module** completion is recalculated: $$(CompletedLessons / TotalLessonsInModule) * 100$$
3.  **Course** completion is recalculated: $$(TotalCompletedLessons / TotalLessonsInCourse) * 100$$

---

## 5. Technical Challenges & Learnings
* **JSON Overheads:** Implementing indexing manually highlighted how much overhead is involved in maintaining pointers to data in a flat file.
* **Race Conditions:** Using `fcntl` provided hands-on experience with file descriptors and the importance of locking mechanisms in multi-threaded environments.
* **Over-Engineering for Education:** Purposely building a complex DAL for a simple JSON store provided a clear "sandbox" to understand how enterprise-grade ORMs and Database Drivers function under the hood.

---
