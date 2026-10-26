"""
tests/test_finbuddy.py
Comprehensive test suite for FinBuddy: DB layer, Auth, Agent Tools, Audit Engine, and APIs.
"""

import os
import pytest
from fastapi.testclient import TestClient

TEST_DB = "test_finbuddy.db"
os.environ["DATABASE_URL"] = f"sqlite:///./{TEST_DB}"

import core.db as db
db.DATABASE_URL = os.environ["DATABASE_URL"]
db.DB_PATH = TEST_DB

from core.db import (
    setup_database,
    create_user,
    get_user_by_username,
    store_transaction,
    fetch_recent_transactions,
    delete_transaction,
    set_category_budget,
    fetch_budget_vs_actual,
    fetch_financial_metrics,
    store_message,
    fetch_chat_history,
    clear_chat_memory,
    export_transactions_csv_data,
)
from core.auth import hash_pin, verify_pin, create_access_token, decode_access_token
from core.knowledge import search_knowledge
from core.audit import compute_health_score
from main import app


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    setup_database()
    yield
    if os.path.exists(TEST_DB):
        try:
            os.remove(TEST_DB)
        except Exception:
            pass


def test_auth_pin_and_jwt():
    pin = "1234"
    hashed = hash_pin(pin)
    assert verify_pin(pin, hashed) is True
    assert verify_pin("9999", hashed) is False

    token = create_access_token(user_id=1, username="alex")
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "1"
    assert decoded["username"] == "alex"


def test_user_management():
    pin_hash = hash_pin("5678")
    user_id = create_user("demouser", pin_hash)
    assert user_id > 0

    user = get_user_by_username("demouser")
    assert user is not None
    assert user["id"] == user_id


def test_transactions_and_budgets():
    pin_hash = hash_pin("4321")
    user_id = create_user("finance_tester", pin_hash)

    # Store transactions
    txn1 = store_transaction(user_id, "2026-10-01", 50000.0, "income", "salary", "Monthly salary")
    txn2 = store_transaction(user_id, "2026-10-02", 4500.0, "expense", "food", "Groceries")
    assert txn1 > 0
    assert txn2 > 0

    txns = fetch_recent_transactions(user_id, limit=5)
    assert len(txns) == 2

    # Set budget
    set_category_budget(user_id, "food", 6000.0)
    budgets = fetch_budget_vs_actual(user_id, "2026-10-01", "2026-10-31")
    assert len(budgets) >= 1
    food_b = next(b for b in budgets if b["category"] == "food")
    assert food_b["monthly_limit"] == 6000.0
    assert food_b["spent"] == 4500.0
    assert food_b["status"] == "safe"

    # Delete transaction
    deleted = delete_transaction(user_id, txn2)
    assert deleted is True
    txns_after = fetch_recent_transactions(user_id, limit=5)
    assert len(txns_after) == 1


def test_chat_memory_and_csv_export():
    pin_hash = hash_pin("1111")
    user_id = create_user("chat_tester", pin_hash)

    store_message(user_id, "user", "Hello FinBuddy")
    store_message(user_id, "bot", "Hello! How can I help with your finances?")

    history = fetch_chat_history(user_id)
    assert "[user] Hello FinBuddy" in history
    assert "[bot] Hello!" in history

    clear_chat_memory(user_id)
    history_cleared = fetch_chat_history(user_id)
    assert history_cleared == ""

    csv_data = export_transactions_csv_data(user_id)
    assert "ID,Date,Type,Category,Amount (INR)" in csv_data


def test_health_score_calculation():
    metrics = {
        "income": 60000.0,
        "expense": 25000.0,
        "savings_rate": 58.3,
        "transaction_count": 12,
        "budget_breakdown": [{"category": "food", "status": "safe"}],
    }
    score, rating = compute_health_score(metrics)
    assert score >= 80
    assert rating in ("Good", "Excellent")


def test_knowledge_retrieval():
    res = search_knowledge("50/30/20")
    assert "50% for Needs" in res

    sip_res = search_knowledge("SIP investment")
    assert "Systematic Investment Plan" in sip_res or "SIP" in sip_res


def test_sip_simulation():
    # SIP math test
    p = 5000.0
    r = (12.0 / 100.0) / 12.0
    n = 5 * 12
    fv = p * (((1 + r) ** n - 1) / r) * (1 + r)
    total_invested = p * n
    assert round(total_invested, 2) == 300000.0
    assert fv > total_invested
    assert round(fv - total_invested, 2) > 100000.0


def test_healthcheck_api():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

