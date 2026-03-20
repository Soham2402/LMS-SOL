1. Courses exist
    content_type -> video, quizes, pdfs, article

2. Features
    a. User Enrollment
    b. Progress Tracking
    c. flexible content management ? <- not sure

3. User -> Admin Instructor Student 

4. Course
    Modules 
        Lessons 

lessons make module, modules make a course

5. Progress Tracking


Essentially I have to build Udemy



Features:
    CreateCourses
    Enrollment (hence user authorization and authentication)
    User Progress Tracking

I need a DAL which allows easy switching of data sources seperating it from the Buisness and application level logic

# Schema 
## Course structure 
### All the tables will contain the basic info like description, title etc
- Courses: Will contain a list of modules and author_id
- Modules: Will contain a list of modules with a course attached to it
- Lessons: Will contain meta_data (gives us flexibity based on content type), info about content

## User Structure
### Ill have 2 tables. One being User, this will host all basic info about an account like email,Created on, hashed password, and user_role etc. Another table will be an AdminProfile (This is technically not needed), InstructorProfile (hosts info about  the courses they own and other metadata) 
StudentProfile Hosts info about the enrolled courses. This also gives us the flexibility that an Instructor can have multiple roles and can watch courses as well as we can directly join with the user table by adding an extra role in the user entry itself. Also allows us to create different unique db structure for each unique role type

- User: username, email, hashedpassword, created_on, is_verified, roles: (list), last_login, gender
- StudentProfile: user_id, enrolled_courses, completed_coutses (optionsl), preferences (basic meta_data)
- InstructorProfile: user_id, courses_createdd(list), ratings, total_reviews, total_courses: int
- AdminProfile: user_id, permissions: []

## Enrollment and Progress
This is the interesting bit
Everytime the user enrolls to a course a new entry will be created in the enrollment table
structure as follows : user_id, course_id, status, completed_percentage, last_lesson
Whenevrr a user starts a new lesson / module a new entry will be created in LessonProgress and ModuleProgress respectively with meta_data about their resspective completion rate

- completed_percentage = completed_lessons/total_lessons*100
- module_completion = completed_lessons_in_module/total_lessons_in_module*100
- Lessonlevel completion will be more about application logic as it will depend on the lesson type to dictate its completion strategy
>for VideoLessons we can simply calculate the last_timestamp for %
>for Articcles we can check if the user has scrolled till end
>This needs to be extinsible in the application level logic


# Dal Implementaion
I will implement a DAL using the repository pattern as it is an industry standard. This dal is 
not going to be generic and only focus on this project itself as the main goal from my vision 
would be to easily switch between data sources

I am going to implement a relatively simple DAL with repositories for every single database model. I will for now use a simple json, with the keys as the model name. 
When the app initializes i will index the json based on the some key (for instance user_id, module_id)
