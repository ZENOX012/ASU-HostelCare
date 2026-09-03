from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import GymInfo, User
from backend.schemas import GymInfoUpdateRequest
from backend.routers.auth import require_roles, get_current_user

router = APIRouter(prefix="/api/gym", tags=["Gym Facility"])

@router.get("")
def get_gym_details(db: Session = Depends(get_db)):
    """Retrieves current gym schedule, rules, facilities, and trainer info."""
    gym = db.query(GymInfo).filter(GymInfo.id == 1).first()
    if not gym:
        # Create default if not exists
        gym = GymInfo(id=1)
        db.add(gym)
        db.commit()
        db.refresh(gym)

    return {
        "id": gym.id,
        "morning_timings": gym.morning_timings,
        "evening_timings": gym.evening_timings,
        "facilities": gym.facilities.split("\n") if gym.facilities else [],
        "facilities_raw": gym.facilities or "",
        "rules": gym.rules.split("\n") if gym.rules else [],
        "rules_raw": gym.rules or "",
        "trainer_name": gym.trainer_name,
        "trainer_contact": gym.trainer_contact,
        "updated_at": gym.updated_at
    }

@router.put("")
def update_gym_details(
    payload: GymInfoUpdateRequest,
    warden: User = Depends(require_roles("warden")),
    db: Session = Depends(get_db)
):
    """Warden updates gym timings, facilities list, rules, and trainer contacts."""
    gym = db.query(GymInfo).filter(GymInfo.id == 1).first()
    if not gym:
        gym = GymInfo(id=1)
        db.add(gym)

    gym.morning_timings = payload.morning_timings.strip()
    gym.evening_timings = payload.evening_timings.strip()
    gym.facilities = payload.facilities.strip()
    gym.rules = payload.rules.strip()
    gym.trainer_name = payload.trainer_name.strip()
    gym.trainer_contact = payload.trainer_contact.strip()

    db.commit()
    db.refresh(gym)

    return {
        "success": True,
        "message": "Gym facility details and guidelines updated successfully."
    }
