"""
core/llm.py
Gemini API interaction bridge for FinBuddy.

Provides backward-compatible call_gemini() and hooks into the
advanced agentic engine (core/agent.py) and vision scanner (core/vision.py).
"""

import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv
import google.genai as genai

from core.agent import run_financial_agent, _fallback_call

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env")

client = genai.Client(api_key=API_KEY)
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


def call_gemini(prompt: str) -> tuple[str, Optional[dict]]:
    """
    Backward-compatible single-call wrapper.
    Returns: (text_reply: str, transaction: dict | None)
    """
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        response_text = response.text.strip()
    except Exception as e:
        logger.error("Gemini API call failed: %s", e)
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return "⚠️ Gemini API quota exceeded (429 RESOURCE_EXHAUSTED). Please check your Gemini API plan or switch models.", None
        return "⚠ I'm having trouble connecting right now. Please try again in a moment.", None

    return _parse_response(response_text)


def _parse_response(response_text: str) -> tuple[str, Optional[dict]]:
    """Parse legacy EXTRACTED_JSON block if present."""
    marker = "EXTRACTED_JSON:"
    if marker not in response_text:
        return response_text, None

    text_part, json_part = response_text.split(marker, 1)
    text_part = text_part.strip()

    try:
        start = json_part.find("{")
        end = json_part.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return text_part, None

        raw_json = json_part[start:end + 1]
        transaction = json.loads(raw_json)

        if "amount" in transaction:
            transaction["amount"] = float(transaction["amount"])
        if "type" in transaction:
            transaction["type"] = str(transaction["type"]).lower()

        return text_part, transaction
    except Exception as e:
        logger.warning("Failed to parse transaction JSON: %s", e)
        return text_part, None
