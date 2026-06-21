"""
routers/api.py
Protected API endpoints. All routes require a valid session cookie.

Endpoints:
  GET  /chat              → Chat page (HTML)
  POST /api/chat          → Send a message, get a reply (JSON)
  GET  /dashboard         → Dashboard page (HTML)
  GET  /api/summary       → Monthly income/expense summary (JSON)
  GET  /api/categories    → Spending by category for current month (JSON)
  GET  /api/transactions  → Recent transactions list (JSON)
"""

from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.auth import get_current_user
from core.db import (
    store_transaction, fetch_recent_transactions,
    store_message, fetch_chat_history,
    fetch_spending_by_category, fetch_monthly_summary,
)
from core.llm import call_gemini
from prompts.finance_prompt import build_chat_prompt

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────

@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "chat.html", {
        "username": user["username"]
    })


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse(request, "dashboard.html", {
        "username": user["username"]
    })


# ─────────────────────────────────────────────
# Chat API
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
def chat(body: ChatRequest, user=Depends(get_current_user)):
    """
    Main chat endpoint.
    1. Save user message
    2. Fetch context (history + recent transactions)
    3. Build prompt and call Gemini
    4. Parse reply and optional transaction
    5. Save bot reply (and transaction if extracted)
    6. Return JSON to frontend
    """
    user_id = user["user_id"]
    user_input = body.message.strip()

    if not user_input:
        return JSONResponse({"reply": "Please type a message.", "transaction_saved": False})

    # Persist user message
    store_message(user_id, "user", user_input)

    # Load context
    chat_history = fetch_chat_history(user_id, limit=12)
    recent_transactions = fetch_recent_transactions(user_id, limit=5)

    # Build prompt and call LLM
    prompt = build_chat_prompt(user_input, recent_transactions, chat_history)
    reply, transaction = call_gemini(prompt)

    # Persist bot reply
    store_message(user_id, "bot", reply)

    # Save transaction if the model extracted one
    transaction_saved = False
    if transaction:
        try:
            store_transaction(
                user_id=user_id,
                date=transaction.get("date", str(date.today())),
                amount=float(transaction["amount"]),
                type_=transaction.get("type", "expense"),
                category=transaction.get("category", "misc"),
                description=transaction.get("description", ""),
            )
            transaction_saved = True
        except Exception:
            # Don't crash the chat if the transaction save fails
            pass

    return JSONResponse({
        "reply": reply,
        "transaction_saved": transaction_saved,
        "transaction": transaction,
    })


# ─────────────────────────────────────────────
# Dashboard Data APIs
# ─────────────────────────────────────────────

@router.get("/api/summary")
def get_summary(user=Depends(get_current_user)):
    """Return monthly income vs expense totals — used by the trend chart."""
    data = fetch_monthly_summary(user["user_id"])
    return JSONResponse(data)


@router.get("/api/categories")
def get_categories(user=Depends(get_current_user)):
    """Return spending by category for the current month — used by the donut chart."""
    today = date.today()
    start = today.replace(day=1).isoformat()
    end = today.isoformat()
    data = fetch_spending_by_category(user["user_id"], start, end)
    return JSONResponse(data)


@router.get("/api/transactions")
def get_transactions(user=Depends(get_current_user), limit: int = 20):
    """Return the N most recent transactions."""
    data = fetch_recent_transactions(user["user_id"], limit=limit)
    return JSONResponse(data)
