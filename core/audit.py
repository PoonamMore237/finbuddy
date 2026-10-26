"""
core/audit.py
Autonomous AI Financial Health Audit & Diagnostic Engine.

Calculates multi-dimensional financial health score and generates
personalized diagnostic reports with spending anomaly detection.
"""

import os
import json
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

import google.genai as genai
from google.genai import types

from core.db import fetch_financial_metrics, fetch_recent_transactions

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


class AuditRecommendation(BaseModel):
    action: str = Field(description="Concrete recommendation")
    estimated_monthly_savings: float = Field(description="Estimated monthly savings in INR if implemented")
    priority: str = Field(description="High, Medium, or Low")


class AuditReport(BaseModel):
    summary: str = Field(description="Executive summary of user's financial posture")
    strengths: List[str] = Field(description="2-3 positive financial habits detected")
    risk_alerts: List[str] = Field(description="1-3 warnings or overspending leakage areas")
    action_plan: List[AuditRecommendation] = Field(description="3 high-leverage recommendations")


def compute_health_score(metrics: dict) -> tuple[int, str]:
    """Calculates a deterministic 0-100 score based on savings, debt, and budget adherence."""
    score = 50  # baseline

    income = metrics.get("income", 0)
    expense = metrics.get("expense", 0)
    savings_rate = metrics.get("savings_rate", 0)
    txn_count = metrics.get("transaction_count", 0)
    budget_breakdown = metrics.get("budget_breakdown", [])

    # Savings rate factor (max +25 / min -25)
    if income > 0:
        if savings_rate >= 30:
            score += 25
        elif savings_rate >= 15:
            score += 15
        elif savings_rate >= 5:
            score += 5
        elif savings_rate < 0:
            score -= 25
    else:
        # If no income logged yet, baseline score depends on spending control
        if expense > 0:
            score -= 10

    # Budget adherence factor (max +15 / min -20)
    exceeded_count = sum(1 for b in budget_breakdown if b.get("status") == "exceeded")
    warning_count = sum(1 for b in budget_breakdown if b.get("status") == "warning")
    if exceeded_count == 0 and len(budget_breakdown) > 0:
        score += 15
    elif exceeded_count == 1:
        score -= 5
    elif exceeded_count >= 2:
        score -= 15
    if warning_count >= 2:
        score -= 5

    # Tracking diligence factor (max +10)
    if txn_count >= 10:
        score += 10
    elif txn_count >= 3:
        score += 5

    score = max(10, min(100, score))

    if score >= 85:
        rating = "Excellent"
    elif score >= 70:
        rating = "Good"
    elif score >= 50:
        rating = "Fair"
    else:
        rating = "Needs Attention"

    return score, rating


def generate_financial_audit(user_id: int) -> dict:
    """
    Combines deterministic financial score with Gen AI diagnostic audit.
    """
    metrics = fetch_financial_metrics(user_id)
    score, rating = compute_health_score(metrics)
    recent_txns = fetch_recent_transactions(user_id, limit=12)

    prompt = f"""You are a certified senior financial planner and AI auditor.
Audit the following user's financial profile:
- Current Month Income: ₹{metrics['income']:,.2f}
- Current Month Expenses: ₹{metrics['expense']:,.2f}
- Net Savings: ₹{metrics['net_savings']:,.2f}
- Savings Rate: {metrics['savings_rate']}%
- Health Score: {score}/100 ({rating})
- Top Expense Categories: {json.dumps(metrics['top_categories'])}
- Budget Adherence: {json.dumps(metrics['budget_breakdown'])}
- Recent Transaction History: {json.dumps(recent_txns)}

Deliver a clear, actionable audit report formatted according to the schema.
Estimate realistic monthly rupee savings for each recommended action.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AuditReport,
                temperature=0.2,
            )
        )
        ai_data = json.loads(response.text)
    except Exception as e:
        logger.error("AI audit generation failed: %s", e)
        ai_data = {
            "summary": f"Your current financial health score is {score}/100 with a rating of '{rating}'.",
            "strengths": ["Active logging of recent transactions"],
            "risk_alerts": ["Review your top expense categories to maintain a 20%+ savings buffer."],
            "action_plan": [
                {"action": "Apply the 50/30/20 budgeting rule to cap discretionary spending", "estimated_monthly_savings": 3000.0, "priority": "High"},
                {"action": "Set category budget limits for your highest spend items", "estimated_monthly_savings": 2000.0, "priority": "Medium"},
            ]
        }

    return {
        "score": score,
        "rating": rating,
        "metrics": metrics,
        "report": ai_data,
    }
