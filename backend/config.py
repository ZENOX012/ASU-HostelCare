import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "ASU HostelCare"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security
    JWT_SECRET_KEY: str = "asu_sec_default_change_in_prod_random_key_92817346"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_URL: str = "sqlite:///./hostelcare.db"

    # Uploads
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    MAX_UPLOAD_SIZE_MB: int = 5

    # Rate Limiting
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10
    AUTH_MAX_FAILED_ATTEMPTS: int = 5
    PUBLIC_RATE_LIMIT_PER_MINUTE: int = 30
    USER_RATE_LIMIT_PER_MINUTE: int = 120

    # Admin Initial Credentials
    SEED_ADMIN_EMAIL: str = "admin@asu.edu"
    SEED_ADMIN_PASSWORD: str = "admin123"
    SEED_ADMIN_NAME: str = "Hostel Warden Office"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
