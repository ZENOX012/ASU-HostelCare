import time
import math
from typing import Dict, List, Optional
from collections import defaultdict
from fastapi import Request, HTTPException, status
from backend.config import settings

class SlidingWindowLimiter:
    def __init__(self):
        # Maps key -> list of timestamp floats
        self.requests: Dict[str, List[float]] = defaultdict(list)
        # Maps account_identifier / ip -> dict(failures=int, unlock_at=float)
        self.auth_backoffs: Dict[str, Dict[str, float]] = defaultdict(lambda: {"failures": 0, "unlock_at": 0.0})

    def _clean_window(self, key: str, window_seconds: int, now: float):
        cutoff = now - window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

    def check_limit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.time()
        self._clean_window(key, window_seconds, now)
        if len(self.requests[key]) >= limit:
            return False
        self.requests[key].append(now)
        return True

    def check_auth_backoff(self, ip: str, account_key: Optional[str] = None) -> Optional[int]:
        """Returns retry-after in seconds if currently in exponential backoff delay."""
        now = time.time()
        # Check IP backoff
        ip_state = self.auth_backoffs.get(f"ip:{ip}")
        if ip_state and ip_state["unlock_at"] > now:
            return math.ceil(ip_state["unlock_at"] - now)
        
        # Check account backoff if provided
        if account_key:
            acc_state = self.auth_backoffs.get(f"acc:{account_key.lower()}")
            if acc_state and acc_state["unlock_at"] > now:
                return math.ceil(acc_state["unlock_at"] - now)
        return None

    def record_auth_failure(self, ip: str, account_key: Optional[str] = None):
        now = time.time()
        # IP failure tracking
        ip_state = self.auth_backoffs[f"ip:{ip}"]
        ip_state["failures"] += 1
        
        # Exponential backoff calculation
        failures = ip_state["failures"]
        if failures >= settings.AUTH_MAX_FAILED_ATTEMPTS:
            # 2s, 4s, 8s, 16s, up to 120s max
            delay = min(120, 2 ** (failures - settings.AUTH_MAX_FAILED_ATTEMPTS + 1))
            ip_state["unlock_at"] = now + delay

        if account_key:
            acc_state = self.auth_backoffs[f"acc:{account_key.lower()}"]
            acc_state["failures"] += 1
            acc_failures = acc_state["failures"]
            if acc_failures >= settings.AUTH_MAX_FAILED_ATTEMPTS:
                delay = min(180, 2 ** (acc_failures - settings.AUTH_MAX_FAILED_ATTEMPTS + 1))
                acc_state["unlock_at"] = now + delay

    def record_auth_success(self, ip: str, account_key: Optional[str] = None):
        self.auth_backoffs.pop(f"ip:{ip}", None)
        if account_key:
            self.auth_backoffs.pop(f"acc:{account_key.lower()}", None)

limiter = SlidingWindowLimiter()

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

def rate_limit_auth(request: Request, account_email: Optional[str] = None):
    ip = get_client_ip(request)
    
    # 1. Check exponential backoff
    retry_after = limiter.check_auth_backoff(ip, account_email)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please wait {retry_after} seconds before retrying.",
            headers={"Retry-After": str(retry_after)}
        )

    # 2. Check requests per minute
    if not limiter.check_limit(f"auth_ip:{ip}", settings.AUTH_RATE_LIMIT_PER_MINUTE, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Authentication rate limit reached. Please wait a minute before trying again.",
            headers={"Retry-After": "60"}
        )

def rate_limit_public(request: Request):
    ip = get_client_ip(request)
    if not limiter.check_limit(f"pub_ip:{ip}", settings.PUBLIC_RATE_LIMIT_PER_MINUTE, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Public query rate limit exceeded. Please slow down.",
            headers={"Retry-After": "30"}
        )

def rate_limit_user(user_id: int):
    if not limiter.check_limit(f"user_id:{user_id}", settings.USER_RATE_LIMIT_PER_MINUTE, 60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="User action rate limit reached. Please slow down.",
            headers={"Retry-After": "15"}
        )
