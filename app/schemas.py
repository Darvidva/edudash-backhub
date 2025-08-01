from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    username: str
    full_name: str
    email: EmailStr
    password: str
    institution: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str = None
    institution: str = None

    class Config:
        orm_mode = True

class CourseBase(BaseModel):
    name: str
    code: str
    credits: int
    difficulty: str
    instructor: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: int
    class Config:
        orm_mode = True


class SemesterBase(BaseModel):
    name: str
    gpa: float
    credits: int

class SemesterCreate(SemesterBase):
    pass

class SemesterResponse(SemesterBase):
    id: int
    class Config:
        orm_mode = True
