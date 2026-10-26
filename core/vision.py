"""
core/vision.py
Multimodal Vision AI for Receipts, Invoices, and Bills.

Extracts structured transaction details, vendor/merchant names, items,
dates, and amounts using Gemini Vision and Pydantic schemas.
"""

import os
import json
import logging
from datetime import date
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

import google.genai as genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


class ReceiptExtraction(BaseModel):
    merchant: str = Field(description="Name of store, merchant, company, or service provider")
    date: str = Field(description="Date on receipt in YYYY-MM-DD format")
    total_amount: float = Field(description="Total final bill amount paid")
    tax_amount: float = Field(default=0.0, description="Taxes included if itemized (e.g. GST, VAT)")
    type: str = Field(default="expense", description="Must be 'expense' or 'income'")
    category: str = Field(
        description="Best matching category: food, groceries, transport, utilities, shopping, health, entertainment, misc"
    )
    line_items: List[str] = Field(default_factory=list, description="List of individual items or services purchased")
    confidence_score: float = Field(default=0.9, description="Confidence in extraction (0.0 to 1.0)")
    summary: str = Field(description="One-sentence human readable summary of this purchase")


def analyze_receipt(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """
    Analyzes an uploaded receipt/invoice image using Gemini Multimodal Vision.
    Returns structured data adhering to ReceiptExtraction.
    """
    today_str = date.today().strftime("%Y-%m-%d")

    prompt = f"""You are an expert financial auditor and receipt OCR specialist.
Inspect this receipt, bill, or invoice image carefully.
Extract the merchant name, date, total amount, taxes, category, item list, and a brief summary.
If the date is missing, illegible, or incomplete, default to today's date: {today_str}.
Ensure the total_amount is a positive numeric float without currency symbols.
"""

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReceiptExtraction,
                temperature=0.1,
            )
        )
        data = json.loads(response.text)
        return {
            "success": True,
            "data": data,
        }
    except Exception as e:
        logger.error("Vision receipt analysis failed: %s", e)
        return {
            "success": False,
            "error": str(e),
            "data": {
                "merchant": "Unknown Merchant",
                "date": today_str,
                "total_amount": 0.0,
                "tax_amount": 0.0,
                "type": "expense",
                "category": "misc",
                "line_items": [],
                "confidence_score": 0.0,
                "summary": "Could not automatically parse receipt. Please verify image clarity.",
            }
        }
