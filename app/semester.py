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
