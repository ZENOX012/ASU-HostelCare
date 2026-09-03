import time
import random
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Notification
from backend.schemas import (
    UserRegisterRequest, UserLoginRequest, UserOtpLoginRequest, 
    GoogleSimLoginRequest, TokenResponse, UserOut
)
from backend.security import (
    hash_password, verify_password, create_access_token, 
    decode_access_token, security_scheme
)
from backend.rate_limiter import (
    rate_limit_auth, limiter, get_client_ip
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory temporary OTP store: email -> dict(otp: str, expires_at: float)
otp_store: Dict[str, Dict[str, Any]] = {}

def get_current_user(
    token_auth = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency that extracts and validates current user from JWT Bearer token."""
    if not token_auth or not token_auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )
    payload = decode_access_token(token_auth.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session."
        )
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists."
        )
    if user.status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Please contact the administrator."
        )
    return user

def require_roles(*roles: str):
    """Dependency factory restricting access to specified roles. Admin has automatic access to warden roles."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        allowed = set(roles)
        # Admin is supreme university authority; has access to all warden resources
        if "warden" in allowed:
            allowed.add("admin")
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(roles)}"
            )
        return user
    return role_checker

@router.post("/register")
def register_student(
    request: Request,
    payload: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Student registration endpoint. 
    Account is created in PENDING_APPROVAL status.
    Login is blocked until approved by Warden.
    """
    rate_limit_auth(request, payload.email)
    
    # Check if email is already taken
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Hash password with PBKDF2-SHA256
    hashed_pw = hash_password(payload.password)

    new_user = User(
        email=payload.email.lower(),
        hashed_password=hashed_pw,
        full_name=payload.full_name,
        role="student",
        status="PENDING_APPROVAL",
        phone=payload.phone,
        hostel_block=payload.hostel_block,
        room_number=payload.room_number,
        address=payload.address,
        profile_photo="/frontend/assets/default_avatar.svg"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Notify all wardens
    wardens = db.query(User).filter(User.role == "warden").all()
    for w in wardens:
        notif = Notification(
            user_id=w.id,
            title="New Student Registration",
            message=f"{new_user.full_name} ({new_user.email}, Block: {new_user.hostel_block}, Room: {new_user.room_number}) has registered and awaits approval.",
            link="/admin/dashboard.html#approvals"
        )
        db.add(notif)
    db.commit()

    return {
        "success": True,
        "message": "Registration successful! Your application is pending Warden approval. You will be able to log in once approved.",
        "user_id": new_user.id
    }

@router.post("/login", response_model=TokenResponse)
def login_with_password(
    request: Request,
    payload: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Secure password authentication with PBKDF2-SHA256,
    per-IP & per-account exponential backoff rate limiting,
    and Warden approval check.
    """
    ip = get_client_ip(request)
    email_clean = payload.email.lower()
    
    rate_limit_auth(request, email_clean)

    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        limiter.record_auth_failure(ip, email_clean)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Check approval status for students
    if user.role == "student" and user.status == "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending Warden approval. Please wait for the hostel administration to approve your profile."
        )
    
    if user.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your registration application was rejected by the Warden. Please contact the hostel office."
        )

    if user.status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is suspended. Please contact the administrator."
        )

    # Reset failure counters upon success
    limiter.record_auth_success(ip, email_clean)

    token = create_access_token(data={"sub": str(user.id), "role": user.role, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/otp/send")
@router.post("/send-otp")
def send_otp_simulation(
    request: Request,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Sends a simulated 6-digit OTP to the student's registered mobile or email.
    Includes OTP in response for interactive test demonstration.
    """
    rate_limit_auth(request)
    phone = str(payload.get("phone", "")).strip()
    email = str(payload.get("email", "")).strip().lower()

    user = None
    digits = "".join(filter(str.isdigit, phone))[-10:] if phone else ""
    if digits:
        user = db.query(User).filter(User.phone.contains(digits)).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        target = phone or email or "provided details"
        raise HTTPException(status_code=404, detail=f"No registered account found with {target}.")

    otp_code = f"{random.randint(100000, 999999)}"
    key = user.email.lower()
    otp_store[key] = {
        "otp": otp_code,
        "expires_at": time.time() + 300
    }
    if digits:
        otp_store[digits] = {
            "otp": otp_code,
            "email": key,
            "expires_at": time.time() + 300
        }

    return {
        "success": True,
        "message": f"Verification code sent to {user.phone or user.email}.",
        "demo_otp": otp_code,
        "simulated_otp": otp_code
    }

@router.post("/otp/verify")
@router.post("/verify-otp")
def verify_otp_and_login(
    request: Request,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    phone = str(payload.get("phone", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    otp = str(payload.get("otp", "")).strip()

    stored = None
    user = None
    if email and email in otp_store:
        stored = otp_store.get(email)
        user = db.query(User).filter(User.email == email).first()
    elif phone:
        digits = "".join(filter(str.isdigit, phone))[-10:]
        if digits in otp_store:
            stored = otp_store.get(digits)
            user_email = stored.get("email")
            user = db.query(User).filter(User.email == user_email).first()
        else:
            user = db.query(User).filter(User.phone.contains(digits)).first()
            if user and user.email in otp_store:
                stored = otp_store.get(user.email)

    if not stored or stored.get("expires_at", 0) < time.time() or stored.get("otp") != otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code.")

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.role == "student" and user.status == "PENDING_APPROVAL":
        raise HTTPException(
            status_code=403, 
            detail="Your account is pending Warden approval."
        )

    # Invalidate OTP
    if email:
        otp_store.pop(email, None)
    if phone:
        digits = "".join(filter(str.isdigit, phone))[-10:]
        otp_store.pop(digits, None)

    token = create_access_token(data={"sub": str(user.id), "role": user.role, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/google-sim", response_model=TokenResponse)
@router.post("/google", response_model=TokenResponse)
def google_simulation_login(
    request: Request,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Simulated Google Single-Sign-On login for registered accounts.
    """
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")
        
    rate_limit_auth(request, email)
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"No account linked with Google email '{email}'. Please complete registration first."
        )

    if user.role == "student" and user.status == "PENDING_APPROVAL":
        raise HTTPException(
            status_code=403,
            detail="Your account is registered but still pending Warden approval."
        )

    token = create_access_token(data={"sub": str(user.id), "role": user.role, "email": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserOut)
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Returns profile information for the authenticated user."""
    return user
