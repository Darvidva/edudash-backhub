from fastapi import APIRouter, Depends, HTTPException
from .schemas import CourseCreate, CourseResponse
from .database import db
from .dependencies import get_current_user
from bson import ObjectId

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)

@router.post("/", response_model=CourseResponse)
def add_course(
    course: CourseCreate,
    user=Depends(get_current_user)
):
    course_doc = course.dict()
    course_doc["user_id"] = str(user["_id"])
    course_doc["_id"] = ObjectId()
    db.courses.insert_one(course_doc)
    course_doc["_id"] = str(course_doc["_id"])
    return CourseResponse(**course_doc)

@router.get("/", response_model=list[CourseResponse])
def get_courses(
    user=Depends(get_current_user)
):
    courses = list(db.courses.find({"user_id": str(user["_id"])}))
    for course in courses:
        course["_id"] = str(course["_id"])
    return [CourseResponse(**course) for course in courses]

@router.delete("/{course_id}")
def delete_course(
    course_id: str,
    user=Depends(get_current_user)
):
    result = db.courses.delete_one({"_id": ObjectId(course_id), "user_id": str(user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted"}

@router.get("/count")
def get_course_count(
    user=Depends(get_current_user)
):
    count = db.courses.count_documents({"user_id": str(user["_id"])})
    return {"total": count}

