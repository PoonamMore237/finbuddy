"""
core/agent.py
Advanced Gen AI Agentic Engine for FinBuddy.

Features:
- Native Tool Calling / Function Execution with Gemini
- Structured multi-step agent reasoning trace (Thoughts, Tool Actions, Observations)
- Grounded database queries & live transaction mutation
- Financial Knowledge Base RAG retrieval
- Mathematical SIP & Wealth Compound Simulation
- Budget management via natural dialogue
"""

import os
import json
import logging
from datetime import date, datetime
from typing import Optional, Any
from dotenv import load_dotenv

import google.genai as genai
from google.genai import types

from core.db import (
    store_transaction,
    fetch_financial_metrics,
    set_category_budget,
    fetch_budgets,
    fetch_recent_transactions,
)
from core.knowledge import search_knowledge

load_dotenv()
logger = logging.getLogger(__name__)

import streamlit as st

load_dotenv()

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or st.secrets.get("GEMINI_API_KEY", "")
)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
client = genai.Client(api_key=GEMINI_API_KEY)

def build_system_instruction() -> str:
    today_str = date.today().strftime("%Y-%m-%d")
    return f"""You are **FinBuddy**, a high-intelligence AI personal finance agent.

## Core Capabilities & Tools
You have live access to tools to manage and analyze the user's financial life:
1. `log_transaction`: Whenever the user mentions spending, earning, paying, or buying something, invoke this tool immediately to log it.
2. `get_financial_summary`: When the user asks about their spending, budget balance, savings rate, or financial status, call this tool to inspect their live database metrics.
3. `set_category_budget`: When the user specifies a budget target or limit for a category (e.g., 'set grocery budget to 8000').
4. `simulate_sip_wealth`: When the user asks about investing, compounding, future savings, or wealth projections.
5. `search_financial_rules`: When the user asks about financial frameworks (50/30/20 rule, emergency funds, tax deductions 80C, debt avalanche).

## Behavioral Principles
- Today's date is: {today_str}. Default to this date when logging transactions if no date is specified.
- Use Indian Rupee (₹) as the primary currency symbol.
- Always be proactive, empowering, and direct.
- Explain key insights concisely using bullet points and markdown.
- If asked off-topic non-finance questions, politely decline and steer back to personal money management.
"""


def run_financial_agent(user_id: int, user_message: str, chat_history_str: str = "") -> dict:
    """
    Executes the multi-turn agentic workflow with real tools.
    Captures tool mutations and returns reasoning steps for frontend transparency.
    """
    reasoning_steps = []
    mutations = {
        "transaction_saved": False,
        "transaction": None,
        "budget_updated": False,
        "budget": None,
    }

    # Define tool implementations bound to the current user's session
    def log_transaction(amount: float, type: str, category: str, description: str = "", date_str: str = "") -> str:
        """Log an income or expense transaction to the user's account. Type must be 'income' or 'expense'."""
        d = date_str.strip() if date_str else date.today().isoformat()
        t = type.strip().lower()
        if t not in ("income", "expense"):
            t = "expense"
        c = category.strip().lower() if category else "misc"
        desc = description.strip() if description else f"{c.capitalize()} transaction"

        try:
            amt = float(amount)
            txn_id = store_transaction(
                user_id=user_id,
                date=d,
                amount=amt,
                type_=t,
                category=c,
                description=desc,
            )
            mutations["transaction_saved"] = True
            mutations["transaction"] = {
                "id": txn_id,
                "date": d,
                "amount": amt,
                "type": t,
                "category": c,
                "description": desc,
            }
            res = f"Transaction logged successfully (ID: {txn_id}, ₹{amt} {t} in {c})"
            reasoning_steps.append({
                "action": "log_transaction",
                "args": {"amount": amt, "type": t, "category": c, "description": desc, "date": d},
                "result": res,
            })
            return res
        except Exception as e:
            err = f"Failed to log transaction: {str(e)}"
            reasoning_steps.append({"action": "log_transaction", "error": err})
            return err

    def get_financial_summary(month: str = "") -> dict:
        """Fetch real-time financial metrics for the current user including income, expense, net savings, and category spend."""
        metrics = fetch_financial_metrics(user_id)
        reasoning_steps.append({
            "action": "get_financial_summary",
            "args": {"month": month or "current"},
            "result": {
                "income": metrics["income"],
                "expense": metrics["expense"],
                "savings_rate": f"{metrics['savings_rate']}%",
                "top_categories": metrics["top_categories"],
            }
        })
        return metrics

    def set_budget(category: str, monthly_limit: float) -> str:
        """Set a monthly budget spending limit for a specific category."""
        c = category.strip().lower()
        limit = float(monthly_limit)
        set_category_budget(user_id, c, limit)
        mutations["budget_updated"] = True
        mutations["budget"] = {"category": c, "monthly_limit": limit}
        res = f"Monthly budget for '{c}' set to ₹{limit:,.2f}"
        reasoning_steps.append({
            "action": "set_category_budget",
            "args": {"category": c, "monthly_limit": limit},
            "result": res,
        })
        return res

    def simulate_sip_wealth(monthly_investment: float, annual_return_rate_pct: float = 12.0, years: int = 10) -> dict:
        """Simulate compound wealth growth from a monthly systematic investment plan (SIP)."""
        p = float(monthly_investment)
        r = float(annual_return_rate_pct) / 100.0 / 12.0
        n = int(years) * 12
        if r > 0:
            future_value = p * (((1 + r) ** n - 1) / r) * (1 + r)
        else:
            future_value = p * n
        total_invested = p * n
        wealth_gain = future_value - total_invested

        # Inflation adjusted at 6%
        inflation_rate = 0.06
        real_value = future_value / ((1 + inflation_rate) ** years)

        out = {
            "monthly_investment": p,
            "duration_years": years,
            "annual_return_pct": annual_return_rate_pct,
            "total_invested": round(total_invested, 2),
            "estimated_future_value": round(future_value, 2),
            "estimated_wealth_gain": round(wealth_gain, 2),
            "inflation_adjusted_purchasing_power": round(real_value, 2),
        }
        reasoning_steps.append({
            "action": "simulate_sip_wealth",
            "args": {"monthly_investment": p, "annual_return_rate_pct": annual_return_rate_pct, "years": years},
            "result": out,
        })
        return out

    def search_financial_rules(topic: str) -> str:
        """Search authoritative personal finance concepts, tax rules (80C, ELSS), and 50/30/20 guidelines."""
        info = search_knowledge(topic)
        reasoning_steps.append({
            "action": "search_financial_rules",
            "args": {"topic": topic},
            "result": "Retrieved domain rules",
        })
        return info

    tools = [log_transaction, get_financial_summary, set_budget, simulate_sip_wealth, search_financial_rules]

    # Assemble contextual prompt
    user_prompt = f"""[Recent Chat Context]
{chat_history_str if chat_history_str else "No prior messages in session."}

[User's Current Message]
{user_message}
"""

    try:
        chat = client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(
                system_instruction=build_system_instruction(),
                tools=tools,
                temperature=0.3,
            )
        )
        response = chat.send_message(user_prompt)
        reply_text = response.text.strip() if response.text else "Done! Let me know if you need any other financial help."

    except Exception as e:
        logger.error("Agent execution failed, falling back to defensive parser: %s", e)
        # Fallback to direct prompt if AFC encounters an issue
        reply_text, fallback_txn = _fallback_call(user_message, user_id)
        if fallback_txn:
            mutations["transaction_saved"] = True
            mutations["transaction"] = fallback_txn

    return {
        "reply": reply_text,
        "reasoning_steps": reasoning_steps,
        "transaction_saved": mutations["transaction_saved"],
        "transaction": mutations["transaction"],
        "budget_updated": mutations["budget_updated"],
        "budget": mutations["budget"],
    }


def _fallback_call(user_message: str, user_id: int) -> tuple[str, Optional[dict]]:
    """Defensive fallback in case tool execution has a network or SDK mismatch."""
    today_str = date.today().strftime("%Y-%m-%d")
    prompt = f"""You are FinBuddy, a helpful personal finance assistant.
Today: {today_str}

If the user mentions an expense or income, emit:
EXTRACTED_JSON: {{"date": "{today_str}", "amount": <number>, "type": "income"|"expense", "category": "<string>", "description": "<string>"}}

User message: {user_message}
"""
    try:
        resp = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        text = resp.text.strip()
        if "EXTRACTED_JSON:" in text:
            parts = text.split("EXTRACTED_JSON:", 1)
            clean_reply = parts[0].strip()
            raw_json = parts[1].strip()
            start = raw_json.find("{")
            end = raw_json.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(raw_json[start:end+1])
                txn_id = store_transaction(
                    user_id=user_id,
                    date=data.get("date", today_str),
                    amount=float(data["amount"]),
                    type_=data.get("type", "expense"),
                    category=data.get("category", "misc"),
                    description=data.get("description", ""),
                )
                data["id"] = txn_id
                return clean_reply, data
        return text, None
    except Exception as err:
        logger.error("Fallback call also failed: %s", err)
        err_msg = str(err)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return (
                "⚠️ **Gemini API Quota Exceeded (429 Resource Exhausted)**: "
                "The free-tier daily request limit for this model has been reached on your Gemini API key. "
                "Please wait for your quota to reset or configure a different model in `.env`.",
                None,
            )
        return "I encountered an issue contacting the Gemini AI service. Please try again in a moment.", None
