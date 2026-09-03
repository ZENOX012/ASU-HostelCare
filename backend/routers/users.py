from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import User, Notification, Complaint
from backend.schemas import (
    UserOut, UserProfileUpdateRequest, PasswordResetRequest, 
    WorkerCreateRequest, WardenCreateRequest, StatusUpdateRequest
)
from backend.security import hash_password
from backend.routers.auth import get_current_user, require_roles
from backend.uploads import validate_and_save_upload
from backend.rate_limiter import rate_limit_user

router = APIRouter(prefix="/api/users", tags=["Users & Profiles"])

@router.put("/profile", response_model=UserOut)
def update_profile(
    payload: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates editable profile attributes for the current user.
    """
    rate_limit_user(current_user.id)
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        current_user.phone = payload.phone.strip()
    if payload.hostel_block is not None:
        current_user.hostel_block = payload.hostel_block.strip()
    if payload.room_number is not None:
        current_user.room_number = payload.room_number.strip()
    if payload.address is not None:
        current_user.address = payload.address.strip()

    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/profile-photo")
def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads and updates profile image with full magic-byte and size validation.
    """
    rate_limit_user(current_user.id)
    photo_url = validate_and_save_upload(file, subfolder="avatars")
    current_user.profile_photo = photo_url
    db.commit()
    db.refresh(current_user)
    return {
        "success": True,
        "message": "Profile photo updated successfully.",
        "profile_photo": photo_url
    }

@router.post("/{user_id}/photo")
def upload_user_photo_by_id(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Allows uploading photo for a student during registration prior to sign-in approval."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    photo_url = validate_and_save_upload(file, subfolder="avatars")
    user.profile_photo = photo_url
    db.commit()
    return {
        "success": True,
        "message": "Photo uploaded successfully.",
        "profile_photo": photo_url
    }

# ==================== WARDEN ONLY ENDPOINTS ====================

@router.get("/pending", response_model=List[UserOut])
def get_pending_registrations(
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Warden reviews all student registrations waiting for approval."""
    pending = db.query(User).filter(User.status == "PENDING_APPROVAL").order_by(User.created_at.desc()).all()
    return pending

@router.post("/{user_id}/status")
def update_user_status(
    user_id: int,
    payload: StatusUpdateRequest,
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Warden approves or rejects a student's registration."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    new_status = payload.status.upper()
    if new_status not in ["APPROVED", "REJECTED", "SUSPENDED", "PENDING_APPROVAL"]:
        raise HTTPException(status_code=400, detail="Invalid status value.")

    target_user.status = new_status
    db.commit()

    # Notify student
    notif_msg = f"Your hostel registration has been {new_status.lower()} by the Warden."
    if new_status == "APPROVED":
        notif_msg = "Congratulations! Your registration has been approved. You can now access all hostel facilities."
    elif new_status == "REJECTED":
        notif_msg = "Your registration was not approved. Please visit the warden office for clarification."

    db.add(Notification(
        user_id=target_user.id,
        title=f"Registration {new_status.capitalize()}",
        message=notif_msg,
        link="/login.html"
    ))
    db.commit()

    return {"success": True, "message": f"User status updated to {new_status}."}

@router.get("/workers", response_model=List[UserOut])
def get_all_workers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns all active workers (used for dispatch and staff views)."""
    workers = db.query(User).filter(User.role == "worker").order_by(User.full_name.asc()).all()
    return workers

@router.post("/workers", response_model=UserOut)
def create_worker_account(
    payload: WorkerCreateRequest,
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Warden creates a staff/worker account."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed_pw = hash_password(payload.password)
    worker = User(
        email=payload.email.lower(),
        hashed_password=hashed_pw,
        full_name=payload.full_name,
        role="worker",
        status="APPROVED",
        phone=payload.phone,
        worker_specialization=payload.worker_specialization,
        worker_shift=payload.worker_shift,
        profile_photo="/frontend/assets/default_avatar.svg"
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker

@router.post("/wardens", response_model=UserOut)
def create_warden_account(
    payload: WardenCreateRequest,
    current_admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    """ONLY Super-Admin creates a Warden account."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed_pw = hash_password(payload.password)
    new_warden = User(
        email=payload.email.lower(),
        hashed_password=hashed_pw,
        full_name=payload.full_name,
        role="warden",
        status="APPROVED",
        phone=payload.phone or "+91 98765 00001",
        hostel_block=payload.hostel_block or "Admin Wing",
        room_number=payload.room_number or "W-01",
        address="Hostel Warden Headquarters, ASU Campus",
        profile_photo="/frontend/assets/default_avatar.svg"
    )
    db.add(new_warden)
    db.commit()
    db.refresh(new_warden)
    return new_warden

@router.get("/all", response_model=List[UserOut])
def list_all_users(
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Warden lists all accounts for directory and password reset."""
    users = db.query(User).order_by(User.id.desc()).all()
    return users

@router.get("/students")
def list_all_students(
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """
    Returns all registered students with complaint counts, room, block, and status.
    """
    students = db.query(User).filter(User.role == "student").order_by(User.created_at.desc()).all()
    results = []
    for s in students:
        total_comp = db.query(Complaint).filter(Complaint.student_id == s.id).count()
        pending_comp = db.query(Complaint).filter(Complaint.student_id == s.id, Complaint.status != "Resolved").count()
        resolved_comp = db.query(Complaint).filter(Complaint.student_id == s.id, Complaint.status == "Resolved").count()
        results.append({
            "id": s.id,
            "full_name": s.full_name,
            "email": s.email,
            "phone": s.phone,
            "hostel_block": s.hostel_block,
            "room_number": s.room_number,
            "address": s.address,
            "status": s.status,
            "profile_photo": s.profile_photo or "/frontend/assets/default_avatar.svg",
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "total_complaints": total_comp,
            "pending_complaints": pending_comp,
            "resolved_complaints": resolved_comp
        })
    return results

@router.get("/students/{student_id}/complaints")
def get_student_complaints(
    student_id: int,
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """
    Returns full complaint history and resolution records for a specific student.
    """
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    complaints = db.query(Complaint).filter(Complaint.student_id == student_id).order_by(Complaint.created_at.desc()).all()
    return {
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "email": student.email,
            "phone": student.phone,
            "hostel_block": student.hostel_block,
            "room_number": student.room_number,
            "address": student.address,
            "status": student.status,
            "profile_photo": student.profile_photo or "/frontend/assets/default_avatar.svg",
            "created_at": student.created_at.isoformat() if student.created_at else None
        },
        "complaints": [
            {
                "id": c.id,
                "ticket_code": c.ticket_code,
                "category": c.category,
                "title": c.title,
                "description": c.description,
                "priority": c.priority,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "assigned_worker_name": c.assigned_worker.full_name if c.assigned_worker else "Unassigned",
                "photo_evidence": c.photo_evidence,
                "resolution_photo": c.resolution_photo,
                "completion_notes": c.completion_notes,
                "student_rating": c.student_rating
            }
            for c in complaints
        ]
    }

@router.post("/reset-password")
def warden_reset_password(
    payload: PasswordResetRequest,
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """
    Hostel Warden can securely reset the password for any student or worker account.
    Self-service reset is deliberately disabled as per university hostel security policy.
    """
    target = db.query(User).filter(User.id == payload.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found.")

    target.hashed_password = hash_password(payload.new_password)
    db.commit()

    db.add(Notification(
        user_id=target.id,
        title="Password Reset by Warden",
        message=f"Your account password was updated by the Warden ({warden.full_name}). Use your new credentials to log in.",
        link="/login.html"
    ))
    db.commit()

    return {"success": True, "message": f"Password for {target.full_name} ({target.email}) was reset successfully."}
