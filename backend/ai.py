import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.models import Complaint, User

EMERGENCY_KEYWORDS = [
    "fire", "spark", "electric shock", "short circuit", "smoke", "wire burning", 
    "gas leak", "flood", "water pipe burst", "ceiling falling", "collapse", 
    "snake", "intruder", "theft", "broken glass"
]

HIGH_KEYWORDS = [
    "leak", "leaking", "no water", "no electricity", "blackout", "geyser", 
    "geyser not working", "fan stopped", "fan not working", "door lock broken", 
    "lock jammed", "toilet choked", "drain choked", "foul smell", "stink", 
    "wifi down", "no internet", "ac down", "ac leaking", "food contaminated", 
    "insect in food", "gym cable snapped", "loose wire"
]

LOW_KEYWORDS = [
    "paint", "scratch", "curtain", "mirror smudge", "dust", "fan speed slow", 
    "slow internet", "wifi slow", "bulb flickering", "table chipped", "aesthetic"
]

def predict_priority(category: str, title: str, description: str) -> Dict[str, str]:
    """
    AI heuristic classifier that inspects complaint text and category to determine urgency.
    """
    combined_text = f"{title} {description} {category}".lower()

    for kw in EMERGENCY_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", combined_text):
            return {
                "priority": "Emergency",
                "confidence": "94%",
                "reason": f"Detected critical safety / emergency keyword: '{kw}'."
            }

    for kw in HIGH_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", combined_text):
            return {
                "priority": "High",
                "confidence": "88%",
                "reason": f"Identified urgent operational impairment keyword: '{kw}'."
            }

    for kw in LOW_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", combined_text):
            return {
                "priority": "Low",
                "confidence": "82%",
                "reason": f"Identified non-critical aesthetic / minor issue keyword: '{kw}'."
            }

    return {
        "priority": "Medium",
        "confidence": "75%",
        "reason": "Standard operational issue with moderate turnaround priority."
    }

def detect_duplicates(
    db: Session,
    category: str,
    sub_category: str,
    title: str,
    description: str,
    hostel_block: Optional[str] = None,
    room_number: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Scans active complaints to find potential duplicates based on shared keywords,
    category, and spatial proximity (same hostel block / room).
    """
    active_statuses = ["Submitted", "Assigned", "In Progress", "Awaiting Confirmation"]
    
    # Query recent active complaints in the same category
    query = db.query(Complaint).join(User, Complaint.student_id == User.id)\
        .filter(Complaint.category == category, Complaint.status.in_(active_statuses))
    
    if hostel_block:
        query = query.filter(User.hostel_block == hostel_block)
        
    candidates = query.limit(25).all()
    duplicates = []

    words_in = set(re.findall(r"\w{4,}", f"{title} {description}".lower()))
    
    for c in candidates:
        words_existing = set(re.findall(r"\w{4,}", f"{c.title} {c.description}".lower()))
        if not words_in or not words_existing:
            continue
        
        intersection = words_in.intersection(words_existing)
        union = words_in.union(words_existing)
        jaccard = len(intersection) / len(union) if union else 0.0

        same_room = (c.student.room_number == room_number) if (c.student and room_number) else False

        if jaccard >= 0.35 or same_room:
            score_pct = int(min(98, max(40, (jaccard * 100) + (35 if same_room else 0))))
            duplicates.append({
                "complaint_code": c.complaint_code,
                "title": c.title,
                "status": c.status,
                "filed_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
                "similarity_score": f"{score_pct}%",
                "room": c.student.room_number if c.student else "N/A",
                "block": c.student.hostel_block if c.student else "N/A"
            })

    # Sort duplicates by similarity descending
    duplicates.sort(key=lambda x: int(x["similarity_score"].replace("%", "")), reverse=True)
    return duplicates[:3]
