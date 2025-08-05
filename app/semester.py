from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from .database import db
from .schemas import SemesterCreate, SemesterResponse, CourseCreate, CourseResponse
from .dependencies import get_current_user

router = APIRouter(prefix="/semesters", tags=["Semesters"])

@router.post("/", response_model=SemesterResponse)
def create_semester(semester: SemesterCreate, user=Depends(get_current_user)):
    sem_doc = semester.dict()
    sem_doc["user_id"] = str(user["_id"])
    sem_doc["courses"] = []
    result = db.semesters.insert_one(sem_doc)
    sem_doc["_id"] = str(result.inserted_id)
    return SemesterResponse(**sem_doc)

@router.get("/", response_model=list[SemesterResponse])
def get_semesters(user=Depends(get_current_user)):
    semesters = list(db.semesters.find({"user_id": str(user["_id"])}))
    for sem in semesters:
        sem["_id"] = str(sem["_id"])
        for course in sem.get("courses", []):
            course["_id"] = str(course["_id"])
    return [SemesterResponse(**sem) for sem in semesters]

@router.post("/{semester_id}/courses", response_model=CourseResponse)
def add_course(semester_id: str, course: CourseCreate, user=Depends(get_current_user)):
    course_doc = course.dict()
    course_doc["_id"] = ObjectId()
    result = db.semesters.update_one(
        {"_id": ObjectId(semester_id), "user_id": str(user["_id"])},
        {"$push": {"courses": course_doc}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Semester not found")
    course_doc["_id"] = str(course_doc["_id"])
    return CourseResponse(**course_doc)

@router.delete("/courses/{course_id}")
def delete_course(course_id: str, user=Depends(get_current_user)):
    result = db.semesters.update_one(
        {"user_id": str(user["_id"]), "courses._id": ObjectId(course_id)},
        {"$pull": {"courses": {"_id": ObjectId(course_id)}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted successfully"}

@router.get("/cgpa")
def get_cgpa(user=Depends(get_current_user)):
    semesters = list(db.semesters.find({"user_id": str(user["_id"])}))
    grade_point_map = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}
    total_grade_points = 0
    total_credits = 0
    for sem in semesters:
        for course in sem.get("courses", []):
            gp = grade_point_map.get(course["grade"].upper(), 0)
            total_grade_points += gp * course["unit"]
            total_credits += course["unit"]
    cgpa = total_grade_points / total_credits if total_credits else 0.0
    return {
        "cgpa": round(cgpa, 2),
        "total_credits": total_credits,
        "semester_count": len(semesters)
    }
