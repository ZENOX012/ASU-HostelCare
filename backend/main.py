import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import settings
from backend.database import engine, Base, SessionLocal
from backend.models import User, GymInfo
from backend.security import hash_password
from backend.routers import auth, users, complaints, gym, notifications, reports, inspector

# Configure server-side logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("asu_hostelcare")

def seed_database():
    """Initializes tables and seeds default admin, sample workers, and gym info."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed Super Admin (Supreme Authority above Warden)
        admin = db.query(User).filter(User.email == settings.SEED_ADMIN_EMAIL.lower()).first()
        if not admin:
            logger.info("Seeding default University Super-Admin account...")
            admin = User(
                email=settings.SEED_ADMIN_EMAIL.lower(),
                hashed_password=hash_password(settings.SEED_ADMIN_PASSWORD),
                full_name="University Super Admin",
                role="admin",
                status="APPROVED",
                phone="+91 98765 00001",
                hostel_block="Central Admin Wing",
                room_number="Admin-HQ",
                address="University Central Administration, ASU Campus",
                profile_photo="/frontend/assets/default_avatar.svg"
            )
            db.add(admin)
        else:
            admin.role = "admin"
            admin.full_name = "University Super Admin"
            db.add(admin)

        # Seed sample workers for immediate demonstration of smart dispatch
        sample_workers = [
            {
                "email": "electrician@asu.edu",
                "name": "Ramesh Sharma",
                "phone": "+91 98111 22334",
                "spec": "Electrician",
                "shift": "Day"
            },
            {
                "email": "plumber@asu.edu",
                "name": "Manoj Kumar",
                "phone": "+91 98222 33445",
                "spec": "Plumber",
                "shift": "Day"
            },
            {
                "email": "it_support@asu.edu",
                "name": "Ankit Verma",
                "phone": "+91 98333 44556",
                "spec": "IT",
                "shift": "Day"
            },
            {
                "email": "cleaning@asu.edu",
                "name": "Suresh Yadav",
                "phone": "+91 98444 55667",
                "spec": "Room Cleaning",
                "shift": "Day"
            },
            {
                "email": "gym_tech@asu.edu",
                "name": "Rajesh Pal",
                "phone": "+91 98555 66778",
                "spec": "Gym Tech",
                "shift": "Day"
            }
        ]

        for w_data in sample_workers:
            w_existing = db.query(User).filter(User.email == w_data["email"]).first()
            if not w_existing:
                w_user = User(
                    email=w_data["email"],
                    hashed_password=hash_password("worker123"),
                    full_name=w_data["name"],
                    role="worker",
                    status="APPROVED",
                    phone=w_data["phone"],
                    worker_specialization=w_data["spec"],
                    worker_shift=w_data["shift"],
                    profile_photo="/frontend/assets/default_avatar.svg"
                )
                db.add(w_user)

        # Seed Gym record
        gym_entry = db.query(GymInfo).filter(GymInfo.id == 1).first()
        if not gym_entry:
            logger.info("Seeding default Gym info...")
            gym_entry = GymInfo(id=1)
            db.add(gym_entry)

        db.commit()
    except Exception as e:
        logger.error(f"Error during database seed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing ASU HostelCare server...")
    seed_database()
    yield
    # Shutdown
    logger.info("Shutting down ASU HostelCare server...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Classical University Hostel Complaint Management System with AI and Proof Verification",
    version="1.0.0",
    lifespan=lifespan
)

# Forbidden files & extensions that must NEVER be served to public clients
FORBIDDEN_EXTENSIONS = (
    ".py", ".pyc", ".pyo", ".pyd", ".env", ".db", ".sqlite", ".sqlite3",
    ".sql", ".zip", ".tar", ".gz", ".rar", ".7z", ".bak", ".log",
    ".yaml", ".yml", ".sh", ".bat", ".dockerignore", ".git"
)

FORBIDDEN_PATH_SUBSTRINGS = [
    "/backend/", "/.git", "/.env", "/requirements.txt", "/dockerfile",
    "/procfile", "/runtime.txt", "/docker-compose", "/scratch/", "/data/",
    "/hostelcare.db"
]

@app.middleware("http")
async def anti_scrape_security_middleware(request: Request, call_next):
    raw_path = request.url.path.lower()

    # 1. Anti-Download / Anti-Source-Access Barrier
    for substring in FORBIDDEN_PATH_SUBSTRINGS:
        if substring in raw_path:
            logger.warning(f"BLOCKED unauthorized source access: {raw_path} from {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access to internal system code and server files is strictly prohibited."}
            )

    for ext in FORBIDDEN_EXTENSIONS:
        if raw_path.endswith(ext):
            logger.warning(f"BLOCKED unauthorized file download: {raw_path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Direct download of server files is strictly prohibited."}
            )

    # 2. Process the request
    response = await call_next(request)

    # 3. Defensive Security Headers (Anti-Sniff, Anti-Frame, Anti-Leak)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Global Error Handlers (Zero Information Leakage)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats validation errors into clean user-facing error messages without traces."""
    errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        msg = err.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Input validation error: " + "; ".join(errors)}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith("/api/"):
        # Friendly 404 fallback for web pages
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
        fallback_page = os.path.join(frontend_dir, "index.html")
        if os.path.exists(fallback_page):
            return FileResponse(fallback_page)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches all unexpected exceptions, logs to console, and returns safe response."""
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please contact the hostel warden."}
    )

# Register Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(complaints.router)
app.include_router(gym.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(inspector.router)

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV
    }

# Safe uploaded file serving endpoint
@app.get("/api/uploads/{subfolder}/{filename}")
@app.get("/api/uploads/{filename}")
def serve_upload(filename: str, subfolder: str = ""):
    target_dir = os.path.join(settings.UPLOAD_DIR, subfolder) if subfolder else settings.UPLOAD_DIR
    safe_path = os.path.abspath(os.path.join(target_dir, filename))
    
    # Prevent path traversal
    if not safe_path.startswith(os.path.abspath(settings.UPLOAD_DIR)):
        raise HTTPException(status_code=403, detail="Access denied.")
    
    if not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Requested file not found.")

    response = FileResponse(safe_path)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

# Serve Frontend static assets and HTML pages
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")

if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path), name="frontend")

# Web root routes
@app.get("/")
def serve_root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/login.html")
@app.get("/login")
def serve_login():
    return FileResponse(os.path.join(frontend_path, "login.html"))

@app.get("/register.html")
@app.get("/register")
def serve_register():
    return FileResponse(os.path.join(frontend_path, "register.html"))

@app.get("/track.html")
@app.get("/track")
def serve_track():
    return FileResponse(os.path.join(frontend_path, "track.html"))

# Student Pages
@app.get("/student/dashboard.html")
@app.get("/student")
def serve_student_dashboard():
    return FileResponse(os.path.join(frontend_path, "student", "dashboard.html"))

@app.get("/student/gym.html")
def serve_student_gym():
    return FileResponse(os.path.join(frontend_path, "student", "gym.html"))

@app.get("/student/profile.html")
def serve_student_profile():
    return FileResponse(os.path.join(frontend_path, "student", "profile.html"))

# Admin / Warden Pages
@app.get("/admin/dashboard.html")
@app.get("/admin")
def serve_admin_dashboard():
    return FileResponse(os.path.join(frontend_path, "admin", "dashboard.html"))

@app.get("/admin/staff.html")
def serve_admin_staff():
    return FileResponse(os.path.join(frontend_path, "admin", "staff.html"))

@app.get("/admin/gym.html")
def serve_admin_gym():
    return FileResponse(os.path.join(frontend_path, "admin", "gym.html"))

@app.get("/admin/reports.html")
def serve_admin_reports():
    return FileResponse(os.path.join(frontend_path, "admin", "reports.html"))

@app.get("/admin/database.html")
def serve_admin_database():
    return FileResponse(os.path.join(frontend_path, "admin", "database.html"))

@app.get("/admin/profile.html")
def serve_admin_profile():
    return FileResponse(os.path.join(frontend_path, "admin", "profile.html"))

# Worker Pages
@app.get("/worker/dashboard.html")
@app.get("/worker")
def serve_worker_dashboard():
    return FileResponse(os.path.join(frontend_path, "worker", "dashboard.html"))

@app.get("/worker/profile.html")
def serve_worker_profile():
    return FileResponse(os.path.join(frontend_path, "worker", "profile.html"))
