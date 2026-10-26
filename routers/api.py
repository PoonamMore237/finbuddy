"""
routers/api.py
Protected API endpoints and pages for FinBuddy.

Routes:
  GET    /chat                   → Chat page (HTML)
  POST   /api/chat               → Agentic chat with tools and reasoning steps (JSON)
  POST   /api/scan-receipt       → Multimodal Vision AI receipt scanner (multipart file)
  GET    /dashboard              → Analytics dashboard (HTML)
  GET    /api/summary            → Monthly income/expense trend (JSON)
  GET    /api/categories         → Spending by category for current month (JSON)
  GET    /api/transactions       → List of transactions (JSON)
  POST   /api/transactions       → Create manual transaction (JSON)
  DELETE /api/transactions/{id}  → Delete transaction (JSON)
  GET    /api/budgets            → Budget vs actual spending comparison (JSON)
  POST   /api/budgets            → Set/update monthly budget limit (JSON)
  GET    /api/financial-health   → AI Financial Health Audit & Score (JSON)
  DELETE /api/chat/clear         → Clear conversation memory (JSON)
  GET    /api/export/csv         → Download transactions as CSV
  GET    /health                 → Public service health check
"""

from datetime import datetime, date, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Request, UploadFile, File, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.db import (
    store_transaction,
    delete_transaction,
    fetch_recent_transactions,
    store_message,
    fetch_chat_history,
    clear_chat_memory,
    fetch_spending_by_category,
    fetch_monthly_summary,
    set_category_budget,
    fetch_budget_vs_actual,
    export_transactions_csv_data,
)
from core.agent import run_financial_agent
from core.vision import analyze_receipt
from core.audit import generate_financial_audit

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ─────────────────────────────────────────────
# Public Health Check
# ─────────────────────────────────────────────

@router.get("/health")
def health():
    """Liveness probe for cloud platforms and Docker."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat(), "service": "finbuddy"}



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
# Agentic Chat API
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
def chat(body: ChatRequest, user=Depends(get_current_user)):
    """
    Advanced agentic chat turn:
    1. Persists user prompt
    2. Runs multi-tool financial agent with real-time tool calling
    3. Persists assistant reply
    4. Returns text, reasoning steps, and any transaction or budget mutations
    """
    user_id = user["user_id"]
    user_input = body.message.strip()

    if not user_input:
        return JSONResponse({"reply": "Please enter a message or question.", "transaction_saved": False})

    store_message(user_id, "user", user_input)
    chat_history = fetch_chat_history(user_id, limit=14)

    # Run Autonomous Agent
    agent_result = run_financial_agent(
        user_id=user_id,
        user_message=user_input,
        chat_history_str=chat_history,
    )

    store_message(user_id, "bot", agent_result["reply"])

    return JSONResponse(agent_result)


@router.delete("/api/chat/clear")
def clear_chat(user=Depends(get_current_user)):
    """Clear conversational memory for the user."""
    clear_chat_memory(user["user_id"])
    return JSONResponse({"success": True, "message": "Conversation history cleared."})


# ─────────────────────────────────────────────
# Multimodal Receipt Scanner API
# ─────────────────────────────────────────────

@router.post("/api/scan-receipt")
async def scan_receipt(
    file: UploadFile = File(...),
    auto_log: bool = Query(default=True),
    user=Depends(get_current_user)
):
    """
    Upload a receipt image (JPEG, PNG, WEBP).
    Uses Gemini Multimodal Vision to extract vendor, date, amount, category, and items.
    If auto_log is true, commits the transaction immediately.
    """
    user_id = user["user_id"]
    contents = await file.read()
    mime_type = file.content_type or "image/jpeg"

    result = analyze_receipt(image_bytes=contents, mime_type=mime_type)

    if not result.get("success"):
        return JSONResponse(result, status_code=400)

    extracted = result["data"]
    amount = float(extracted.get("total_amount", 0.0))
    cat = extracted.get("category", "misc").lower()
    merchant = extracted.get("merchant", "Merchant Purchase")
    txn_date = extracted.get("date") or date.today().isoformat()
    desc = f"{merchant} — {', '.join(extracted.get('line_items', [])[:3])}" if extracted.get('line_items') else merchant

    txn_id = None
    if auto_log and amount > 0:
        txn_id = store_transaction(
            user_id=user_id,
            date=txn_date,
            amount=amount,
            type_="expense",
            category=cat,
            description=desc,
        )
        # Also log to chat memory so user has visual transcript
        store_message(user_id, "user", f"[Uploaded Receipt: {merchant}]")
        store_message(user_id, "bot", f"🧾 Logged ₹{amount:,.2f} at **{merchant}** under *{cat}*. Items: {', '.join(extracted.get('line_items', [])[:4])}")

    return JSONResponse({
        "success": True,
        "transaction_id": txn_id,
        "extracted": extracted,
        "message": f"Successfully parsed receipt from {merchant} (₹{amount:,.2f})",
    })


# ─────────────────────────────────────────────
# Dashboard & Analytics APIs
# ─────────────────────────────────────────────

@router.get("/api/summary")
def get_summary(user=Depends(get_current_user)):
    """Monthly income vs expense totals for trend chart."""
    data = fetch_monthly_summary(user["user_id"])
    return JSONResponse(data)


@router.get("/api/categories")
def get_categories(user=Depends(get_current_user)):
    """Category spend breakdown for current month for donut chart."""
    today = date.today()
    start = today.replace(day=1).isoformat()
    end = today.isoformat()
    data = fetch_spending_by_category(user["user_id"], start, end)
    return JSONResponse(data)


@router.get("/api/transactions")
def get_transactions(
    user=Depends(get_current_user),
    limit: int = 50,
    search: Optional[str] = None,
    txn_type: Optional[str] = None
):
    """Return transaction list with optional search and type filtering."""
    data = fetch_recent_transactions(user["user_id"], limit=limit)
    if search:
        s = search.strip().lower()
        data = [t for t in data if s in t["category"].lower() or s in (t.get("description") or "").lower()]
    if txn_type and txn_type.lower() in ("income", "expense"):
        data = [t for t in data if t["type"] == txn_type.lower()]
    return JSONResponse(data)


class ManualTransactionRequest(BaseModel):
    amount: float = Field(gt=0)
    type: str
    category: str
    description: Optional[str] = ""
    date: Optional[str] = None


@router.post("/api/transactions")
def add_transaction(body: ManualTransactionRequest, user=Depends(get_current_user)):
    """Manually add transaction via modal or form."""
    d = body.date or date.today().isoformat()
    txn_id = store_transaction(
        user_id=user["user_id"],
        date=d,
        amount=body.amount,
        type_=body.type,
        category=body.category,
        description=body.description or "",
    )
    return JSONResponse({
        "success": True,
        "transaction_id": txn_id,
        "message": f"Saved ₹{body.amount:,.2f} {body.type}."
    })


@router.delete("/api/transactions/{txn_id}")
def remove_transaction(txn_id: int, user=Depends(get_current_user)):
    """Delete a transaction by ID."""
    success = delete_transaction(user["user_id"], txn_id)
    if not success:
        return JSONResponse({"success": False, "message": "Transaction not found."}, status_code=404)
    return JSONResponse({"success": True, "message": "Transaction deleted."})


# ─────────────────────────────────────────────
# Budgets & Financial Health APIs
# ─────────────────────────────────────────────

@router.get("/api/budgets")
def get_budgets(user=Depends(get_current_user)):
    """Category budget targets vs current month spending."""
    today = date.today()
    start = today.replace(day=1).isoformat()
    end = today.isoformat()
    data = fetch_budget_vs_actual(user["user_id"], start, end)
    return JSONResponse(data)


class BudgetRequest(BaseModel):
    category: str
    monthly_limit: float = Field(gt=0)


@router.post("/api/budgets")
def set_budget(body: BudgetRequest, user=Depends(get_current_user)):
    """Set or update category budget."""
    set_category_budget(user["user_id"], body.category, body.monthly_limit)
    return JSONResponse({
        "success": True,
        "message": f"Budget for {body.category} updated to ₹{body.monthly_limit:,.2f}"
    })


@router.get("/api/financial-health")
def financial_health(user=Depends(get_current_user)):
    """Generates AI Financial Health Audit & Score."""
    audit_data = generate_financial_audit(user["user_id"])
    return JSONResponse(audit_data)


# ─────────────────────────────────────────────
# Data Export API
# ─────────────────────────────────────────────

@router.get("/api/export/csv")
def export_csv(user=Depends(get_current_user)):
    """Export all user transactions as a CSV file attachment."""
    csv_content = export_transactions_csv_data(user["user_id"])
    filename = f"finbuddy_transactions_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
