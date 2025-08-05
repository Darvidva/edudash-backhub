from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from . import schemas
from .database import get_db
from .token import verify_access_token

router = APIRouter(
    prefix="/courses",
    tags=["Courses"]
)

# 🔐 This must match your login endpoint path
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ✅ Dependency to get current user from token
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
    user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return user

# 🚀 Add a new course
@router.post("/", response_model=schemas.CourseResponse)
def add_course(
    course: schemas.CourseCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    new_course = models.Course(**course.dict(), user_id=user.id)
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

# 📄 Get all courses for logged-in user
@router.get("/", response_model=list[schemas.CourseResponse])
def get_courses(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    return db.query(models.Course).filter_by(user_id=user.id).all()

# ❌ Delete a course
@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    course = db.query(models.Course).filter_by(id=course_id, user_id=user.id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found."
        )
    db.delete(course)
    db.commit()
    return {"message": "Course deleted"}


@router.get("/count")
def get_course_count(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user)
):
    count = db.query(models.Course).filter_by(user_id=user.id).count()
    return {"total": count}

