from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, time


class MemberRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = None


class MemberLogin(BaseModel):
    username: str
    password: str


class MemberOut(BaseModel):
    id: int
    username: str
    name: str
    phone: Optional[str]
    remaining_sessions: int
    created_at: str


class CoachRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = None
    specialty: Optional[str] = None


class CoachLogin(BaseModel):
    username: str
    password: str


class CoachOut(BaseModel):
    id: int
    username: str
    name: str
    phone: Optional[str]
    specialty: Optional[str]
    created_at: str


class CourseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price_sessions: int = Field(..., gt=0)
    duration_minutes: int = Field(default=60, gt=0)


class CourseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price_sessions: Optional[int] = Field(None, gt=0)
    duration_minutes: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class CourseOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price_sessions: int
    duration_minutes: int
    is_active: bool
    created_at: str


class BookingCreate(BaseModel):
    member_id: int
    coach_id: int
    course_id: int
    booking_date: date
    start_time: time


class BookingReschedule(BaseModel):
    booking_date: date
    start_time: time


class BookingOut(BaseModel):
    id: int
    member_id: int
    coach_id: int
    course_id: int
    booking_date: str
    start_time: str
    end_time: str
    status: str
    sessions_cost: int
    created_at: str
    updated_at: str


class BookingOutDetail(BaseModel):
    id: int
    member_id: int
    member_name: str
    coach_id: int
    coach_name: str
    course_id: int
    course_name: str
    booking_date: str
    start_time: str
    end_time: str
    status: str
    sessions_cost: int
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    message: str


class SessionTopUp(BaseModel):
    sessions: int = Field(..., gt=0)
