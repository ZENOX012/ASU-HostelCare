from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default="student") # student, warden, worker
    status = Column(String(30), nullable=False, default="PENDING_APPROVAL") # PENDING_APPROVAL, APPROVED, REJECTED, SUSPENDED
    phone = Column(String(20), nullable=True)
    hostel_block = Column(String(50), nullable=True)
    room_number = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    profile_photo = Column(String(255), nullable=True) # file path or url
    
    # Worker specific
    worker_specialization = Column(String(50), nullable=True) # Room Cleaning, Electrician, Plumber, IT, Laundry, Mess, Gym Tech, Maintenance, Security
    worker_shift = Column(String(20), nullable=True) # Day, Night
    
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    complaints_filed = relationship("Complaint", back_populates="student", foreign_keys="Complaint.student_id")
    complaints_assigned = relationship("Complaint", back_populates="worker", foreign_keys="Complaint.assigned_worker_id")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_code = Column(String(40), unique=True, index=True, nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category = Column(String(60), nullable=False) # Room, Internet, Water & Electricity, Laundry, Mess, Gym, Common Areas
    sub_category = Column(String(100), nullable=False)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="Medium") # Low, Medium, High, Emergency
    status = Column(String(40), nullable=False, default="Submitted") # Submitted, Assigned, In Progress, Awaiting Confirmation, Resolved, Rejected
    evidence_photo = Column(String(255), nullable=True)

    # Worker Assignment & Proof
    assigned_worker_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    completion_photo = Column(String(255), nullable=True)
    completion_notes = Column(Text, nullable=True)
    completion_lat = Column(Float, nullable=True)
    completion_lng = Column(Float, nullable=True)
    completion_accuracy = Column(Float, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Student Confirmation & Rating
    student_rating = Column(Integer, nullable=True) # 1 to 5
    student_feedback = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    student = relationship("User", back_populates="complaints_filed", foreign_keys=[student_id])
    worker = relationship("User", back_populates="complaints_assigned", foreign_keys=[assigned_worker_id])
    timeline = relationship("ComplaintTimeline", back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintTimeline.created_at")


class ComplaintTimeline(Base):
    __tablename__ = "complaint_timelines"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    status = Column(String(50), nullable=False)
    action_by_name = Column(String(120), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    complaint = relationship("Complaint", back_populates="timeline")


class GymInfo(Base):
    __tablename__ = "gym_info"

    id = Column(Integer, primary_key=True, index=True)
    morning_timings = Column(String(100), default="06:00 AM – 09:30 AM")
    evening_timings = Column(String(100), default="05:00 PM – 10:00 PM")
    facilities = Column(Text, default="Cardio Zone (4x Treadmills, 2x Ellipticals)\nFree Weights (Dumbbells 2.5kg - 40kg, Olympic Barbell & Squat Rack)\nCable Crossover Machine\nMulti-Gym Strength Stations\nAir Conditioned & Clean Locker Facility\nEmergency First-Aid Station")
    rules = Column(Text, default="1. Clean sports shoes and proper gym wear mandatory.\n2. Re-rack all weights and sanitize equipment after use.\n3. Keep mobile phones on silent; no speaker music.\n4. Maximum 20 minutes on cardio machines during peak hours.\n5. Report any broken cables or loose bolts immediately via ASU HostelCare.")
    trainer_name = Column(String(120), default="Vikramaditya Rao (Certified Strength Coach)")
    trainer_contact = Column(String(50), default="+91 98765 43210 (Ext. 402)")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(160), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="notifications")
