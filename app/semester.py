from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .models import Semester, User
from .schemas import SemesterCreate, SemesterResponse
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
    new_semester = Semester(**semester.dict(), user_id=user.id)
    db.add(new_semester)
    db.commit()
    db.refresh(new_semester)
    return new_semester

@router.get("/", response_model=list[SemesterResponse])
def get_semesters(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return db.query(Semester).filter(Semester.user_id == user.id).all()

@router.put("/{semester_id}", response_model=SemesterResponse)
def update_semester(
    semester_id: int,
    updated_data: SemesterCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    semester = db.query(Semester).filter(Semester.id == semester_id, Semester.user_id == user.id).first()

    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found.")

    semester.gpa = updated_data.gpa
    semester.credits = updated_data.credits
    db.commit()
    db.refresh(semester)
    return semester

@router.delete("/{semester_id}")
def delete_semester(
    semester_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    semester = db.query(Semester).filter(Semester.id == semester_id, Semester.user_id == user.id).first()
    if not semester:
        raise HTTPException(status_code=404, detail="Semester not found.")

    db.delete(semester)
    db.commit()
    return {"message": "Semester deleted successfully"}

@router.get("/cgpa")
def get_cgpa(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Calculate and return the current CGPA based on all semesters"""
    semesters = db.query(Semester).filter(Semester.user_id == user.id).all()
    
    if not semesters:
        return {
            "cgpa": 0.0,
            "total_credits": 0,
            "semester_count": 0,
            "message": "No semester data available"
        }
    
    total_grade_points = 0
    total_credits = 0
    
    for semester in semesters:
        # Calculate grade points for this semester (GPA * credits)
        grade_points = semester.gpa * semester.credits
        total_grade_points += grade_points
        total_credits += semester.credits
    
    if total_credits == 0:
        cgpa = 0.0
    else:
        cgpa = total_grade_points / total_credits
    
    # Get the most recent semester for comparison
    latest_semester = max(semesters, key=lambda s: s.id) if semesters else None
    previous_cgpa = 0.0
    
    if len(semesters) > 1:
        # Calculate CGPA without the latest semester
        other_semesters = [s for s in semesters if s.id != latest_semester.id]
        other_grade_points = sum(s.gpa * s.credits for s in other_semesters)
        other_credits = sum(s.credits for s in other_semesters)
        if other_credits > 0:
            previous_cgpa = other_grade_points / other_credits
    
    cgpa_change = cgpa - previous_cgpa
    
    return {
        "cgpa": round(cgpa, 2),
        "total_credits": total_credits,
        "semester_count": len(semesters),
        "change": round(cgpa_change, 2),
        "latest_semester": latest_semester.name if latest_semester else None
    }
