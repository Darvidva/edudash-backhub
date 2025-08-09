from pydantic import BaseModel, EmailStr, Field, conint
from typing import Optional, List
from datetime import datetime

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

# Study Block schemas for timetable
class StudyBlockBase(BaseModel):
    title: str
    course: str
    startTime: str
    endTime: str
    day: int  # 1-7 (Monday-Sunday)
    duration: int  # minutes
    difficulty: str  # 'easy' | 'medium' | 'hard'
    priority: str  # 'low' | 'medium' | 'high'
    type: str  # 'lecture' | 'study' | 'assignment' | 'exam'
    color: str

class StudyBlockCreate(StudyBlockBase):
    pass

class StudyBlockResponse(StudyBlockBase):
    id: str = Field(..., alias="_id")

# Study Group schemas
class StudyGroupBase(BaseModel):
    name: str
    description: str
    course: str
    max_members: int = 20
    is_private: bool = False
    access_code: Optional[str] = None

class StudyGroupCreate(StudyGroupBase):
    pass

class StudyGroupResponse(StudyGroupBase):
    id: str = Field(..., alias="_id")
    creator_id: str
    members: List[str] = []
    member_count: int = 0
    created_at: datetime
    is_active: bool = True
    last_activity: Optional[datetime] = None

class StudyGroupJoin(BaseModel):
    access_code: Optional[str] = None

# Study Group Member schema
class StudyGroupMemberBase(BaseModel):
    user_id: str
    group_id: str
    role: str = "member"  # "creator", "admin", "member"

class StudyGroupMemberResponse(StudyGroupMemberBase):
    id: str = Field(..., alias="_id")
    joined_at: datetime
    user_info: Optional[dict] = None

# Discussion schemas
class DiscussionMessageBase(BaseModel):
    content: str
    group_id: str

class DiscussionMessageCreate(DiscussionMessageBase):
    pass

class DiscussionMessageResponse(DiscussionMessageBase):
    id: str = Field(..., alias="_id")
    user_id: str
    user_name: str
    user_initials: str
    created_at: datetime
    updated_at: Optional[datetime] = None

# Resource schemas
class GroupResourceBase(BaseModel):
    name: str
    description: Optional[str] = None
    file_type: str
    file_size: int
    group_id: str

class GroupResourceCreate(GroupResourceBase):
    file_content: str  # Base64 encoded file content

class GroupResourceResponse(GroupResourceBase):
    id: str = Field(..., alias="_id")
    uploaded_by: str
    uploader_name: str
    uploaded_at: datetime
    download_url: str

# Group Timetable Event schemas
class GroupTimetableEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    group_id: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    event_type: str = "study_session"  # "study_session", "meeting", "exam_prep", "project_work"

class GroupTimetableEventCreate(GroupTimetableEventBase):
    pass

class GroupTimetableEventResponse(GroupTimetableEventBase):
    id: str = Field(..., alias="_id")
    created_by: str
    creator_name: str
    created_at: datetime
    attendees: List[str] = []
    attendee_count: int = 0

