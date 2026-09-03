import io
import csv
from datetime import datetime
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import Complaint, User
from backend.routers.auth import require_roles

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])

@router.get("/stats")
def get_analytics_stats(
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Provides high-level KPI metrics and category distribution."""
    total_complaints = db.query(Complaint).count()
    submitted = db.query(Complaint).filter(Complaint.status == "Submitted").count()
    assigned = db.query(Complaint).filter(Complaint.status == "Assigned").count()
    in_progress = db.query(Complaint).filter(Complaint.status == "In Progress").count()
    awaiting_conf = db.query(Complaint).filter(Complaint.status == "Awaiting Confirmation").count()
    resolved = db.query(Complaint).filter(Complaint.status == "Resolved").count()

    total_students = db.query(User).filter(User.role == "student", User.status == "APPROVED").count()
    pending_approvals = db.query(User).filter(User.role == "student", User.status == "PENDING_APPROVAL").count()
    total_workers = db.query(User).filter(User.role == "worker").count()

    resolution_rate = round((resolved / total_complaints * 100), 1) if total_complaints > 0 else 0.0

    # Category counts
    category_counts = db.query(
        Complaint.category, func.count(Complaint.id)
    ).group_by(Complaint.category).all()
    categories = {cat: count for cat, count in category_counts}

    # Priority counts
    priority_counts = db.query(
        Complaint.priority, func.count(Complaint.id)
    ).group_by(Complaint.priority).all()
    priorities = {p: count for p, count in priority_counts}

    # Average rating
    avg_rating_query = db.query(func.avg(Complaint.student_rating)).filter(Complaint.student_rating != None).scalar()
    avg_rating = round(float(avg_rating_query), 2) if avg_rating_query else 5.0

    return {
        "total_complaints": total_complaints,
        "submitted": submitted,
        "assigned": assigned,
        "in_progress": in_progress,
        "awaiting_confirmation": awaiting_conf,
        "resolved": resolved,
        "resolution_rate": resolution_rate,
        "total_students": total_students,
        "pending_approvals": pending_approvals,
        "total_workers": total_workers,
        "categories": categories,
        "priorities": priorities,
        "average_rating": avg_rating
    }

@router.get("/export-csv")
def export_complaints_csv(
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """
    Exports all complaints to an Excel-friendly CSV file with UTF-8 BOM,
    including student details, worker details, and geo-tagged coordinates.
    """
    complaints = db.query(Complaint).order_by(Complaint.created_at.desc()).all()

    output = io.StringIO()
    # Write UTF-8 BOM for Microsoft Excel compatibility
    output.write("\ufeff")
    
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    headers = [
        "Complaint Code",
        "Filed Date (UTC)",
        "Student Name",
        "Student Email",
        "Student Phone",
        "Hostel Block",
        "Room Number",
        "Category",
        "Sub-Category",
        "Title",
        "Description",
        "Priority",
        "Status",
        "Assigned Worker",
        "Worker Specialization",
        "Worker Shift",
        "Completed At (UTC)",
        "GPS Latitude",
        "GPS Longitude",
        "GPS Accuracy (m)",
        "Resolved At (UTC)",
        "Rating (1-5)",
        "Student Feedback",
        "Evidence Photo URL",
        "Proof Photo URL"
    ]
    writer.writerow(headers)

    for c in complaints:
        student_name = c.student.full_name if c.student else "N/A"
        student_email = c.student.email if c.student else "N/A"
        student_phone = c.student.phone if c.student else "N/A"
        block = c.student.hostel_block if c.student else "N/A"
        room = c.student.room_number if c.student else "N/A"

        worker_name = c.worker.full_name if c.worker else "Unassigned"
        worker_spec = c.worker.worker_specialization if c.worker else "N/A"
        worker_shift = c.worker.worker_shift if c.worker else "N/A"

        row = [
            c.complaint_code,
            c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
            student_name,
            student_email,
            student_phone,
            block,
            room,
            c.category,
            c.sub_category,
            c.title,
            c.description,
            c.priority,
            c.status,
            worker_name,
            worker_spec,
            worker_shift,
            c.completed_at.strftime("%Y-%m-%d %H:%M:%S") if c.completed_at else "",
            f"{c.completion_lat:.6f}" if c.completion_lat is not None else "",
            f"{c.completion_lng:.6f}" if c.completion_lng is not None else "",
            f"{c.completion_accuracy:.1f}" if c.completion_accuracy is not None else "",
            c.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if c.resolved_at else "",
            c.student_rating or "",
            c.student_feedback or "",
            c.evidence_photo or "",
            c.completion_photo or ""
        ]
        writer.writerow(row)

    csv_data = output.getvalue()
    filename = f"ASU_HostelCare_Export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache"
        }
    )
