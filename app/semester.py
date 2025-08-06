from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from .database import db
from .schemas import SemesterCreate, SemesterResponse, SemesterCourseCreate, SemesterCourseResponse, CGPASummaryResponse
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

from fastapi.responses import JSONResponse

@router.get("/", response_model=list[SemesterResponse])
def get_semesters(user=Depends(get_current_user)):
    try:
        semesters = list(db.semesters.find({"user_id": str(user["_id"])}))
        for sem in semesters:
            sem["_id"] = str(sem["_id"])
            sem["courses"] = sem.get("courses") or []
            for course in sem["courses"]:
                course["_id"] = str(course["_id"])
        return [SemesterResponse(**sem) for sem in semesters]
    except Exception as e:
        print("Error in get_semesters:", e)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@router.post("/{semester_id}/courses", response_model=SemesterCourseResponse)
def add_course(semester_id: str, course: SemesterCourseCreate, user=Depends(get_current_user)):
    course_doc = course.dict()
    course_doc["_id"] = ObjectId()
    result = db.semesters.update_one(
        {"_id": ObjectId(semester_id), "user_id": str(user["_id"])},
        {"$push": {"courses": course_doc}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Semester not found")
    course_doc["_id"] = str(course_doc["_id"])
    return SemesterCourseResponse(**course_doc)

@router.delete("/courses/{course_id}")
def delete_course(course_id: str, user=Depends(get_current_user)):
    result = db.semesters.update_one(
        {"user_id": str(user["_id"]), "courses._id": ObjectId(course_id)},
        {"$pull": {"courses": {"_id": ObjectId(course_id)}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted successfully"}

@router.put("/{sem_id}/courses/{course_id}")
def update_course(sem_id: str, course_id: str, update: dict, user=Depends(get_current_user)):
    result = db.semesters.update_one(
        {"_id": ObjectId(sem_id), "user_id": str(user["_id"]), "courses._id": ObjectId(course_id)},
        {"$set": {
            f"courses.$.{list(update.keys())[0]}": list(update.values())[0]
        }}
    )
    return {"success": result.modified_count > 0}


@router.get("/cgpa/summary", response_model=CGPASummaryResponse)  # define proper Pydantic model
def get_cgpa_summary(user=Depends(get_current_user)):
    semesters = list(db.semesters.find({"user_id": str(user["_id"])}))
    grade_point_map = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}

    cumulative_points = 0
    cumulative_units = 0
    semester_count = len(semesters)
    latest_semester = None

    for sem in semesters:
        sem_points = 0
        sem_units = 0
        for course in sem.get("courses", []):
            unit = course.get("unit", 0)
            grade = (course.get("grade") or "F").upper()
            gp = grade_point_map.get(grade, 0)
            sem_points += gp * unit
            sem_units += unit
        cumulative_points += sem_points
        cumulative_units += sem_units
        if not latest_semester or sem["name"] > latest_semester:
            latest_semester = sem["name"]

    cgpa = (cumulative_points / cumulative_units) if cumulative_units else 0.0

    # For 'change' you might calculate difference from last semester GPA if you want

    return {
        "cgpa": round(cgpa, 2),
        "total_credits": cumulative_units,
        "semester_count": semester_count,
        "change": 0,  # placeholder, implement if you want
        "latest_semester": latest_semester,
    }
