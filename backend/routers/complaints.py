import random
import string
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.database import get_db
from backend.models import Complaint, ComplaintTimeline, User, Notification
from backend.schemas import (
    ComplaintCreateRequest, ComplaintAssignRequest, 
    ComplaintCompleteRequest, ComplaintConfirmRequest, ComplaintOut
)
from backend.routers.auth import get_current_user, require_roles
from backend.uploads import validate_and_save_upload
from backend.ai import predict_priority, detect_duplicates
from backend.rate_limiter import rate_limit_public, rate_limit_user

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

def generate_complaint_code() -> str:
    """Generates unique university complaint tracking code e.g. ASU-2026-4829."""
    rand_digits = "".join(random.choices(string.digits, k=4))
    return f"ASU-2026-{rand_digits}"

# Category to Worker Specialization mapping for smart dispatch
SPECIALIZATION_MAP = {
    "Room": ["Room Cleaning", "Maintenance"],
    "Internet": ["IT"],
    "Water & Electricity": ["Plumber", "Electrician"],
    "Laundry": ["Laundry", "Maintenance"],
    "Mess": ["Mess", "Maintenance"],
    "Gym": ["Gym Tech", "Maintenance"],
    "Common Areas": ["Maintenance", "Room Cleaning", "Security"]
}

@router.post("/ai-analyze")
def analyze_complaint_ai(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI Smart Assistant:
    1. Analyzes title & description to predict urgency/priority.
    2. Detects existing duplicate or related complaints nearby.
    """
    category = payload.get("category", "Room")
    sub_category = payload.get("sub_category", "General")
    title = payload.get("title", "")
    description = payload.get("description", "")

    ai_pred = predict_priority(category, title, description)
    duplicates = detect_duplicates(
        db, category, sub_category, title, description,
        hostel_block=current_user.hostel_block,
        room_number=current_user.room_number
    )

    return {
        "prediction": ai_pred,
        "duplicates": duplicates
    }

@router.post("/upload-evidence")
def upload_complaint_evidence(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Uploads complaint evidence photo with image validation."""
    rate_limit_user(current_user.id)
    url = validate_and_save_upload(file, subfolder="complaints")
    return {"url": url}

@router.post("", response_model=ComplaintOut)
def create_complaint(
    payload: ComplaintCreateRequest,
    current_user: User = Depends(require_roles("student", "warden")),
    db: Session = Depends(get_db)
):
    """Student files a new hostel complaint."""
    rate_limit_user(current_user.id)

    # Generate unique complaint code
    code = generate_complaint_code()
    while db.query(Complaint).filter(Complaint.complaint_code == code).first():
        code = generate_complaint_code()

    # Determine priority (use provided or AI predicted)
    priority = payload.priority or predict_priority(payload.category, payload.title, payload.description)["priority"]

    complaint = Complaint(
        complaint_code=code,
        student_id=current_user.id,
        category=payload.category,
        sub_category=payload.sub_category,
        title=payload.title,
        description=payload.description,
        priority=priority,
        status="Submitted",
        evidence_photo=payload.evidence_photo
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Add initial timeline record
    timeline = ComplaintTimeline(
        complaint_id=complaint.id,
        status="Submitted",
        action_by_name=current_user.full_name,
        notes="Complaint filed by student."
    )
    db.add(timeline)

    # Notify wardens
    wardens = db.query(User).filter(User.role == "warden").all()
    for w in wardens:
        db.add(Notification(
            user_id=w.id,
            title=f"New Complaint [{code}]",
            message=f"{current_user.full_name} filed '{complaint.title}' ({complaint.category} - {complaint.priority} Priority).",
            link=f"/admin/dashboard.html#complaint-{complaint.id}"
        ))

    db.commit()
    db.refresh(complaint)
    return complaint

@router.get("", response_model=List[ComplaintOut])
def list_complaints(
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists complaints based on role:
    - Student: sees their own filed complaints.
    - Worker: sees complaints assigned to them.
    - Warden: sees all hostel complaints.
    """
    query = db.query(Complaint)
    if current_user.role == "student":
        query = query.filter(Complaint.student_id == current_user.id)
    elif current_user.role == "worker":
        query = query.filter(Complaint.assigned_worker_id == current_user.id)
    
    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    if category_filter:
        query = query.filter(Complaint.category == category_filter)

    return query.order_by(desc(Complaint.created_at)).all()

@router.get("/track/{code}", response_model=ComplaintOut)
def track_complaint_public(
    code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public complaint tracking endpoint (No login required).
    Rate-limited to prevent scraping.
    """
    rate_limit_public(request)
    complaint = db.query(Complaint).filter(Complaint.complaint_code == code.strip().upper()).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="No complaint found with this reference code.")
    return complaint

@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint_detail(
    complaint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch complaint details."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    
    # Access check
    if current_user.role == "student" and complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this complaint.")
    if current_user.role == "worker" and complaint.assigned_worker_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this complaint.")

    return complaint

@router.get("/{complaint_id}/dispatch-suggestions")
def get_dispatch_suggestions(
    complaint_id: int,
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """
    Ola/Rapido style smart worker dispatch:
    Suggests workers ordered by matching specialization and active shift.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    matched_specs = SPECIALIZATION_MAP.get(complaint.category, ["Maintenance"])
    all_workers = db.query(User).filter(User.role == "worker", User.status == "APPROVED").all()

    suggestions = []
    for w in all_workers:
        # Check how many active jobs the worker currently has
        active_jobs = db.query(Complaint).filter(
            Complaint.assigned_worker_id == w.id,
            Complaint.status.in_(["Assigned", "In Progress", "Awaiting Confirmation"])
        ).count()

        is_matched_spec = w.worker_specialization in matched_specs
        score = 0
        if is_matched_spec:
            score += 50
        # Prefer workers with fewer active jobs
        score += max(0, 30 - (active_jobs * 10))

        suggestions.append({
            "worker_id": w.id,
            "full_name": w.full_name,
            "phone": w.phone,
            "specialization": w.worker_specialization,
            "shift": w.worker_shift,
            "active_jobs": active_jobs,
            "match_badge": "Best Match" if is_matched_spec else "General Support",
            "score": score
        })

    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return suggestions

@router.post("/{complaint_id}/assign")
def assign_worker(
    complaint_id: int,
    payload: ComplaintAssignRequest,
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Warden assigns a worker to the complaint."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    worker = db.query(User).filter(User.id == payload.worker_id, User.role == "worker").first()
    if not worker:
        raise HTTPException(status_code=400, detail="Specified worker does not exist.")

    complaint.assigned_worker_id = worker.id
    complaint.status = "Assigned"

    db.add(ComplaintTimeline(
        complaint_id=complaint.id,
        status="Assigned",
        action_by_name=warden.full_name,
        notes=f"Assigned to {worker.full_name} ({worker.worker_specialization}, {worker.worker_shift} Shift)."
    ))

    # Notify worker
    db.add(Notification(
        user_id=worker.id,
        title=f"New Task Assigned [{complaint.complaint_code}]",
        message=f"You have been assigned: '{complaint.title}' ({complaint.category}) by {warden.full_name}.",
        link=f"/worker/dashboard.html#task-{complaint.id}"
    ))

    # Notify student
    db.add(Notification(
        user_id=complaint.student_id,
        title=f"Worker Assigned [{complaint.complaint_code}]",
        message=f"{worker.full_name} ({worker.worker_specialization}) has been assigned to your complaint.",
        link=f"/student/dashboard.html#complaint-{complaint.id}"
    ))

    db.commit()
    return {"success": True, "message": f"Complaint assigned to {worker.full_name}."}

@router.post("/{complaint_id}/start")
def worker_start_job(
    complaint_id: int,
    worker: User = Depends(require_roles("worker")),
    db: Session = Depends(get_db)
):
    """Worker begins working on the assigned complaint."""
    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id,
        Complaint.assigned_worker_id == worker.id
    ).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Assigned complaint not found.")

    complaint.status = "In Progress"
    db.add(ComplaintTimeline(
        complaint_id=complaint.id,
        status="In Progress",
        action_by_name=worker.full_name,
        notes="Worker arrived at location and commenced task resolution."
    ))

    # Notify student
    db.add(Notification(
        user_id=complaint.student_id,
        title=f"Work In Progress [{complaint.complaint_code}]",
        message=f"{worker.full_name} is now actively working on your complaint.",
        link=f"/student/dashboard.html#complaint-{complaint.id}"
    ))

    db.commit()
    return {"success": True, "message": "Job marked as In Progress."}

@router.post("/{complaint_id}/complete")
def worker_complete_job(
    complaint_id: int,
    payload: ComplaintCompleteRequest,
    worker: User = Depends(require_roles("worker")),
    db: Session = Depends(get_db)
):
    """
    Worker marks job complete with:
    - Geo-tagged proof photo
    - Live GPS coordinates (lat, lng, accuracy)
    - Completion remarks
    Sets status to 'Awaiting Confirmation' and triggers student review.
    """
    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id,
        Complaint.assigned_worker_id == worker.id
    ).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Assigned complaint not found.")

    complaint.status = "Awaiting Confirmation"
    complaint.completion_photo = payload.completion_photo
    complaint.completion_notes = payload.completion_notes
    complaint.completion_lat = payload.completion_lat
    complaint.completion_lng = payload.completion_lng
    complaint.completion_accuracy = payload.completion_accuracy
    complaint.completed_at = datetime.now(timezone.utc)

    db.add(ComplaintTimeline(
        complaint_id=complaint.id,
        status="Awaiting Confirmation",
        action_by_name=worker.full_name,
        notes=f"Worker submitted completion proof with GPS coordinates ({payload.completion_lat:.5f}, {payload.completion_lng:.5f}). Waiting for student confirmation."
    ))

    # Notify student that action is required
    db.add(Notification(
        user_id=complaint.student_id,
        title=f"Action Required: Confirm Completion [{complaint.complaint_code}]",
        message=f"{worker.full_name} has completed the work. Please inspect and confirm or reject.",
        link=f"/student/dashboard.html#confirm-{complaint.id}"
    ))

    db.commit()
    return {"success": True, "message": "Completion proof submitted. Awaiting student confirmation."}

@router.post("/{complaint_id}/confirm")
def student_confirm_or_reject(
    complaint_id: int,
    payload: ComplaintConfirmRequest,
    student: User = Depends(require_roles("student", "warden")),
    db: Session = Depends(get_db)
):
    """
    Student confirms or rejects the worker's completed job:
    - If confirmed: status becomes 'Resolved', rating & feedback saved.
    - If rejected: status returns to 'In Progress' for rework.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    if student.role == "student" and complaint.student_id != student.id:
        raise HTTPException(status_code=403, detail="Only the student who filed this complaint can confirm resolution.")

    if payload.is_confirmed:
        complaint.status = "Resolved"
        complaint.resolved_at = datetime.now(timezone.utc)
        complaint.student_rating = payload.student_rating
        complaint.student_feedback = payload.student_feedback

        db.add(ComplaintTimeline(
            complaint_id=complaint.id,
            status="Resolved",
            action_by_name=student.full_name,
            notes=f"Resolution confirmed by student. Rating: {payload.student_rating or 'N/A'} Stars. Feedback: {payload.student_feedback or 'Satisfied'}."
        ))

        # Notify worker
        if complaint.assigned_worker_id:
            db.add(Notification(
                user_id=complaint.assigned_worker_id,
                title=f"Job Confirmed [{complaint.complaint_code}]",
                message=f"Student confirmed resolution and awarded you {payload.student_rating or 5} stars!",
                link="/worker/dashboard.html"
            ))
        msg = "Complaint resolution successfully confirmed."
    else:
        complaint.status = "In Progress"
        db.add(ComplaintTimeline(
            complaint_id=complaint.id,
            status="In Progress",
            action_by_name=student.full_name,
            notes=f"Student disputed resolution. Reason: {payload.student_feedback or 'Unsatisfactory resolution'}."
        ))

        # Notify worker to redo
        if complaint.assigned_worker_id:
            db.add(Notification(
                user_id=complaint.assigned_worker_id,
                title=f"Job Reopened [{complaint.complaint_code}]",
                message=f"Student requested further resolution: '{payload.student_feedback or 'Issue persists'}'.",
                link=f"/worker/dashboard.html#task-{complaint.id}"
            ))
        msg = "Complaint reopened for further attention."

    db.commit()
    return {"success": True, "message": msg, "status": complaint.status}
