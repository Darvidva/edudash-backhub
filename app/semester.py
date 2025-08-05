from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .models import Semester, Course, User
from .schemas import SemesterCreate, SemesterResponse, CourseCreate, CourseResponse
from .database import get_db
from .dependencies import get_current_user

router = APIRouter(
    prefix="/semesters",
    tags=["Semesters"]
)

@router.post("/", response_model=SemesterResponse)
def create_semester(
    semester: SemesterCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    new_semester = Semester(name=semester.name, user_id=user.id)
    db.add(new_semester)
    db.flush()  # Get new_semester.id before adding courses
    for course in semester.courses:
        db.add(Course(**course.dict(), semester_id=new_semester.id, user_id=user.id))
    db.commit()
    db.refresh(new_semester)
    return new_semester

@router.get("/", response_model=list[SemesterResponse])
def get_semesters(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db.query(Semester).filter(Semester.user_id == user.id).all()

@router.post("/{semester_id}/courses", response_model=CourseResponse)
def add_course(
    semester_id: int,
    course: CourseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    semester = db.query(Semester).filter(Semester.id == semester_id, Semester.user_id == user.id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found.")
    new_course = Course(**course.dict(), semester_id=semester_id, user_id=user.id)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    course = db.query(Course).join(Semester).filter(Course.id == course_id, Semester.user_id == user.id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}

@router.get("/cgpa")
def get_cgpa(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    semesters = db.query(Semester).filter(Semester.user_id == user.id).all()
    grade_point_map = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}
    total_grade_points = 0
    total_credits = 0

    for semester in semesters:
        for course in semester.courses:
            gp = grade_point_map.get(course.grade.upper(), 0)
            total_grade_points += gp * course.unit
            total_credits += course.unit

    cgpa = total_grade_points / total_credits if total_credits else 0.0
    return {
        "cgpa": round(cgpa, 2),
        "total_credits": total_credits,
        "semester_count": len(semesters)
    }
