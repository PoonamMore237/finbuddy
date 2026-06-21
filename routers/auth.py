"""
routers/auth.py
Handles /register and /login.

Design notes:
- Passwords are sent via form fields (application/x-www-form-urlencoded), not JSON.
  This matches HTML <form> semantics and avoids needing JS for auth.
- The JWT is set as an httpOnly cookie — JS on the page cannot read it,
  which prevents XSS token theft.
- On logout, we simply delete the cookie.
"""

import sqlite3
from fastapi import APIRouter, Form, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.db import create_user, get_user_by_username
from core.auth import hash_pin, verify_pin, create_access_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Redirect root to login page."""
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


# ─────────────────────────────────────────────
# Actions
# ─────────────────────────────────────────────

@router.post("/register")
def register(
    response: Response,
    username: str = Form(...),
    pin: str = Form(...),
):
    """
    Create a new user account.
    PIN must be 4-6 digits. Username is lowercased and trimmed.
    """
    username = username.strip().lower()

    # Basic validation
    if not username or len(username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters.")
    if not pin.isdigit() or not (4 <= len(pin) <= 6):
        raise HTTPException(status_code=400, detail="PIN must be 4–6 digits.")

    pin_hash = hash_pin(pin)

    try:
        user_id = create_user(username, pin_hash)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username already taken.")

    # Log the user in immediately after registration
    token = create_access_token(user_id, username)
    redirect = RedirectResponse(url="/chat", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key="access_token",
        value=token,
        httponly=True,   # JS cannot read this cookie
        samesite="lax",  # CSRF protection
        max_age=60 * 60 * 8  # 8 hours
    )
    return redirect


@router.post("/login")
def login(
    username: str = Form(...),
    pin: str = Form(...),
):
    """
    Authenticate an existing user.
    Returns a 303 redirect to /chat on success, 401 on failure.
    """
    username = username.strip().lower()
    user = get_user_by_username(username)

    if user is None or not verify_pin(pin, user["pin_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or PIN."
        )

    token = create_access_token(user["id"], user["username"])
    redirect = RedirectResponse(url="/chat", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8
    )
    return redirect


@router.post("/logout")
def logout():
    """Clear the session cookie and redirect to login."""
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie("access_token")
    return redirect
