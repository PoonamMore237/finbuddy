"""
core/llm.py
Gemini API interaction layer.

Single responsibility: call Gemini, return (text_reply, extracted_transaction | None).
The prompt lives in prompts/finance_prompt.py — not here.
"""

import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env")

client = genai.Client(api_key=API_KEY)

# Use Flash for speed and cost efficiency. Swap to Pro for richer reasoning if needed.
MODEL = "gemini-2.5-flash"

# ─────────────────────────────────────────────
# Gemini Call
# ─────────────────────────────────────────────

def call_gemini(prompt: str) -> tuple[str, Optional[dict]]:
    """
    Send a prompt to Gemini. Returns:
        (text_reply: str, transaction: dict | None)

    The transaction dict is extracted from the EXTRACTED_JSON: marker
    that the prompt instructs the model to emit when a transaction is detected.

    Error handling:
    - Network/API failures → returns a user-facing error string + None
    - Malformed JSON in the model's output → logs the error, returns None for transaction
      (the conversation continues; the transaction is simply not saved)
    """
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        response_text = response.text.strip()
    except Exception as e:
        logger.error("Gemini API call failed: %s", e)
        return "⚠ I'm having trouble connecting right now. Please try again in a moment.", None

    return _parse_response(response_text)


def _parse_response(response_text: str) -> tuple[str, Optional[dict]]:
    """
    Split the model's output into:
        - The conversational text (shown to user)
        - The structured transaction JSON (saved to DB, if present)

    The model is instructed to emit exactly one EXTRACTED_JSON: block
    when it detects a transaction. Everything before that marker is the reply.
    """
    marker = "EXTRACTED_JSON:"

    if marker not in response_text:
        return response_text, None

    text_part, json_part = response_text.split(marker, 1)
    text_part = text_part.strip()

    # Find the first complete {...} object in whatever the model output after the marker
    try:
        start = json_part.find("{")
        end = json_part.rfind("}")
        if start == -1 or end == -1 or end <= start:
            logger.warning("EXTRACTED_JSON marker found but no valid JSON object: %r", json_part)
            return text_part, None

        raw_json = json_part[start:end + 1]
        transaction = json.loads(raw_json)

        # Normalise amount to float — model sometimes returns a string
        if "amount" in transaction:
            transaction["amount"] = float(transaction["amount"])

        # Normalise type to lowercase
        if "type" in transaction:
            transaction["type"] = str(transaction["type"]).lower()

        return text_part, transaction

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse transaction JSON: %s | raw: %r", e, json_part)
        return text_part, None
