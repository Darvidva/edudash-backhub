from pydantic import BaseModel, EmailStr, Field, conint
from typing import Optional, List

class UserCreate(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    password: str
    institution: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    email: EmailStr
    full_name: Optional[str]
    institution: Optional[str]

class CourseBase(BaseModel):
    name: str
    code: str
    unit: int
    difficulty: Optional[str] = None
    instructor: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: str = Field(..., alias="_id")

# Per-semester course schema for CGPA projection
class SemesterCourseBase(BaseModel):
    name: str
    grade: Optional[str] = None
    unit: conint(ge=0)

class SemesterCourseCreate(SemesterCourseBase):
    pass

class SemesterCourseResponse(SemesterCourseBase):
    id: str = Field(..., alias="_id")

class SemesterBase(BaseModel):
    name: str

class SemesterCreate(SemesterBase):
    courses: List[SemesterCourseCreate] = []

class SemesterResponse(SemesterBase):
    id: str = Field(..., alias="_id")
    courses: List[SemesterCourseResponse] = []

class CGPASummaryResponse(BaseModel):
    cgpa: float
    total_credits: int
    semester_count: int
    change: float
    latest_semester: Optional[str] = None

