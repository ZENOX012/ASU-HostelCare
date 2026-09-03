from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from backend.database import get_db, engine, Base
from backend.models import User, Complaint, ComplaintTimeline, GymInfo, Notification
from backend.routers.auth import require_roles

router = APIRouter(prefix="/api/inspector", tags=["Database Inspector"])

ALLOWED_TABLES = {
    "users": User,
    "complaints": Complaint,
    "complaint_timelines": ComplaintTimeline,
    "gym_info": GymInfo,
    "notifications": Notification
}

@router.get("/tables")
def list_database_tables(
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Lists all SQL tables in the database with schema columns and row counts."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    results = []

    for name in table_names:
        if name in ALLOWED_TABLES:
            model = ALLOWED_TABLES[name]
            count = db.query(model).count()
            cols = [col["name"] for col in inspector.get_columns(name)]
            results.append({
                "table_name": name,
                "row_count": count,
                "columns": cols
            })

    return results

@router.get("/tables/{table_name}")
def view_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """
    Safely inspects rows in a specific table with column details.
    Sensitive password hashes are masked for security.
    """
    clean_name = table_name.strip().lower()
    if clean_name not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=400,
            detail=f"Table '{table_name}' is not in the list of inspectable tables."
        )

    model = ALLOWED_TABLES[clean_name]
    total_rows = db.query(model).count()
    offset = (page - 1) * limit
    
    rows = db.query(model).offset(offset).limit(limit).all()
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(clean_name)]

    data = []
    for r in rows:
        row_dict = {}
        for col in columns:
            val = getattr(r, col, None)
            # Mask password hash for display safety
            if col == "hashed_password":
                val = "pbkdf2_sha256$***[MASKED]***"
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            row_dict[col] = val
        data.append(row_dict)

    return {
        "table_name": clean_name,
        "total_rows": total_rows,
        "page": page,
        "limit": limit,
        "columns": columns,
        "rows": data
    }
