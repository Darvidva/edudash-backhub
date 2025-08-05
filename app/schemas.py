from pydantic import BaseModel, EmailStr, Field
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

    class Config:
        orm_mode = True

class CourseBase(BaseModel):
    name: str
    code: str
    grade: str
    unit: int
    difficulty: Optional[str] = None
    instructor: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: str = Field(..., alias="_id")

class SemesterBase(BaseModel):
    name: str

class SemesterCreate(SemesterBase):
    courses: List[CourseCreate] = []

class SemesterResponse(SemesterBase):
    id: str = Field(..., alias="_id")
    courses: List[CourseResponse] = []

