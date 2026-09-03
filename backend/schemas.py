from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

PHONE_REGEX = re.compile(r"^\+?[0-9\s\-]{7,15}$")

# Auth Schemas
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=7, max_length=15)
    hostel_block: str = Field(..., min_length=1, max_length=50)
    room_number: str = Field(..., min_length=1, max_length=30)
    address: Optional[str] = Field(None, max_length=255)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v_clean = v.strip()
        if not PHONE_REGEX.match(v_clean):
            raise ValueError("Invalid phone number format. Must contain 7 to 15 digits.")
        return v_clean

    @field_validator("full_name", "hostel_block", "room_number")
    @classmethod
    def strip_and_check(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only.")
        return cleaned


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=100)


class UserOtpLoginRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)


class GoogleSimLoginRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class WorkerCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=7, max_length=15)
    worker_specialization: str = Field(..., min_length=2, max_length=50)
    worker_shift: str = Field(default="Day", min_length=2, max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v_clean = v.strip()
        if not PHONE_REGEX.match(v_clean):
            raise ValueError("Invalid phone number format.")
        return v_clean


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, min_length=7, max_length=15)
    hostel_block: Optional[str] = Field(None, min_length=1, max_length=50)
    room_number: Optional[str] = Field(None, min_length=1, max_length=30)
    address: Optional[str] = Field(None, max_length=255)


class PasswordResetRequest(BaseModel):
    user_id: int
    new_password: str = Field(..., min_length=6, max_length=100)


class StatusUpdateRequest(BaseModel):
    status: str = Field(..., min_length=3, max_length=30) # APPROVED, REJECTED, SUSPENDED


# Complaint Schemas
class ComplaintCreateRequest(BaseModel):
    category: str = Field(..., min_length=2, max_length=60)
    sub_category: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=4, max_length=160)
    description: str = Field(..., min_length=10, max_length=2500)
    priority: Optional[str] = Field(default="Medium", min_length=3, max_length=20)
    evidence_photo: Optional[str] = None


class ComplaintAssignRequest(BaseModel):
    worker_id: int


class ComplaintCompleteRequest(BaseModel):
    completion_photo: str = Field(..., min_length=3)
    completion_notes: Optional[str] = Field(None, max_length=1000)
    completion_lat: float = Field(..., ge=-90.0, le=90.0)
    completion_lng: float = Field(..., ge=-180.0, le=180.0)
    completion_accuracy: Optional[float] = None


class ComplaintConfirmRequest(BaseModel):
    is_confirmed: bool # True = Confirm Resolved, False = Reopen / Reject
    student_rating: Optional[int] = Field(None, ge=1, le=5)
    student_feedback: Optional[str] = Field(None, max_length=1000)


# Gym Schemas
class GymInfoUpdateRequest(BaseModel):
    morning_timings: str = Field(..., min_length=3, max_length=100)
    evening_timings: str = Field(..., min_length=3, max_length=100)
    facilities: str = Field(..., min_length=5, max_length=3000)
    rules: str = Field(..., min_length=5, max_length=3000)
    trainer_name: str = Field(..., min_length=2, max_length=120)
    trainer_contact: str = Field(..., min_length=3, max_length=50)


# Response Models
class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    status: str
    phone: Optional[str] = None
    hostel_block: Optional[str] = None
    room_number: Optional[str] = None
    address: Optional[str] = None
    profile_photo: Optional[str] = None
    worker_specialization: Optional[str] = None
    worker_shift: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TimelineOut(BaseModel):
    id: int
    status: str
    action_by_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ComplaintOut(BaseModel):
    id: int
    complaint_code: str
    student_id: int
    category: str
    sub_category: str
    title: str
    description: str
    priority: str
    status: str
    evidence_photo: Optional[str] = None
    assigned_worker_id: Optional[int] = None
    completion_photo: Optional[str] = None
    completion_notes: Optional[str] = None
    completion_lat: Optional[float] = None
    completion_lng: Optional[float] = None
    completion_accuracy: Optional[float] = None
    completed_at: Optional[datetime] = None
    student_rating: Optional[int] = None
    student_feedback: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    student: Optional[UserOut] = None
    worker: Optional[UserOut] = None
    timeline: List[TimelineOut] = []

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
