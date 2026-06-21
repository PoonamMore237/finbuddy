"""
core/auth.py
Authentication utilities for FinBuddy.

Approach:
- Users register with a username + 4-6 digit PIN (not a password, fits the "personal finance app" UX)
- PINs are hashed with bcrypt before storage (never store plaintext)
- On login, a short-lived JWT is issued and stored in an httpOnly cookie
- FastAPI routes use get_current_user() as a dependency to protect endpoints

Why JWT over sessions?
- Stateless: no server-side session table needed
- Works naturally with FastAPI's dependency injection
- Easy to demonstrate in interviews
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from fastapi import Cookie, HTTPException, status
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours — reasonable for a personal app


# ─────────────────────────────────────────────
# PIN Hashing
# ─────────────────────────────────────────────

def hash_pin(plain_pin: str) -> str:
    """Return a bcrypt hash of the given PIN, stored as a UTF-8 string."""
    hashed = bcrypt.hashpw(plain_pin.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Return True if the plain PIN matches the stored hash."""
    return bcrypt.checkpw(plain_pin.encode("utf-8"), hashed_pin.encode("utf-8"))

# ─────────────────────────────────────────────
# JWT Tokens
# ─────────────────────────────────────────────

def create_access_token(user_id: int, username: str) -> str:
    """
    Create a JWT encoding user_id and username.
    Expires in ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),   # subject: the user's id
        "username": username,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT.
    Returns the payload dict, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ─────────────────────────────────────────────
# FastAPI Dependency
# ─────────────────────────────────────────────

def get_current_user(access_token: Optional[str] = Cookie(default=None)) -> dict:
    """
    FastAPI dependency. Reads the JWT from the httpOnly cookie named 'access_token'.
    Raises 401 if missing or invalid. Returns the decoded payload dict.

    Usage in a route:
        @router.get("/dashboard")
        def dashboard(user=Depends(get_current_user)):
            ...
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )

    payload = decode_access_token(access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )

    return {
        "user_id": int(payload["sub"]),
        "username": payload["username"]
    }
