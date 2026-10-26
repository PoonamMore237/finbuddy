"""
core/db.py
Database layer for FinBuddy.

Design decisions:
- Plain sqlite3 (no ORM overhead, fast, zero unnecessary dependencies)
- Normalized schema: transactions, budgets, users, chat_memory
- Robust cloud compatibility: auto-creates parent folders if DATABASE_URL points to a persistent volume (e.g., /data/finbuddy.db)
"""

import sqlite3
import os
import csv
import io
from datetime import datetime, date
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Allow override via env var so tests can use an in-memory DB or Docker mount
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finbuddy.db")
DB_PATH = DATABASE_URL.replace("sqlite:///", "")

# Ensure directory exists if DB_PATH has a directory prefix
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

def setup_database() -> None:
    """Create all tables and indexes if they don't exist. Safe to call on startup."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                pin_hash    TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                date        DATE    NOT NULL,
                amount      REAL    NOT NULL CHECK(amount > 0),
                type        TEXT    NOT NULL CHECK(type IN ('income', 'expense')),
                category    TEXT    NOT NULL DEFAULT 'misc',
                description TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                category      TEXT    NOT NULL,
                monthly_limit REAL    NOT NULL CHECK(monthly_limit > 0),
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_memory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('user', 'bot')),
                message     TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_user_date
                ON transactions(user_id, date);

            CREATE INDEX IF NOT EXISTS idx_chat_memory_user
                ON chat_memory(user_id, id);

            CREATE INDEX IF NOT EXISTS idx_budgets_user
                ON budgets(user_id, category);
        """)


# ─────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────

def create_user(username: str, pin_hash: str) -> int:
    """Insert a new user. Returns user id."""
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, pin_hash) VALUES (?, ?)",
            (username.strip().lower(), pin_hash)
        )
        conn.commit()
        return cursor.lastrowid


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    """Return the user row for a given username, or None if not found."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, username, pin_hash FROM users WHERE username = ?",
            (username.strip().lower(),)
        ).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    """Return the user row for a given id, or None."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()


# ─────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────

def store_transaction(user_id: int, date: str, amount: float,
                      type_: str, category: str, description: str = "") -> int:
    """Insert a transaction. Returns the new transaction id."""
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO transactions (user_id, date, amount, type, category, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, date, amount, type_.lower(), category.lower(), description)
        )
        conn.commit()
        return cursor.lastrowid


def delete_transaction(user_id: int, txn_id: int) -> bool:
    """Delete a transaction belonging to user_id. Returns True if deleted."""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (txn_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def fetch_recent_transactions(user_id: int, limit: int = 15) -> list[dict]:
    """Return the most recent N transactions for a user including id."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, date, amount, type, category, description, created_at
               FROM transactions
               WHERE user_id = ?
               ORDER BY date DESC, id DESC
               LIMIT ?""",
            (user_id, limit)
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_transactions_in_range(user_id: int, start_date: str, end_date: str) -> list[dict]:
    """Return all transactions for a user between two dates (inclusive)."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, date, amount, type, category, description, created_at
               FROM transactions
               WHERE user_id = ? AND date BETWEEN ? AND ?
               ORDER BY date DESC, id DESC""",
            (user_id, start_date, end_date)
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_spending_by_category(user_id: int, start_date: str, end_date: str) -> list[dict]:
    """Return total spending per category for a date range."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE user_id = ? AND type = 'expense' AND date BETWEEN ? AND ?
               GROUP BY category
               ORDER BY total DESC""",
            (user_id, start_date, end_date)
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_monthly_summary(user_id: int) -> list[dict]:
    """Return month-by-month income vs expense totals."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT
                   strftime('%Y-%m', date) AS month,
                   SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expense
               FROM transactions
               WHERE user_id = ?
               GROUP BY month
               ORDER BY month ASC""",
            (user_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def export_transactions_csv_data(user_id: int) -> str:
    """Generate CSV string of all transactions for export."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, date, type, category, amount, description, created_at
               FROM transactions
               WHERE user_id = ?
               ORDER BY date DESC, id DESC""",
            (user_id,)
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Type", "Category", "Amount (INR)", "Description", "Created At"])
    for r in rows:
        writer.writerow([r["id"], r["date"], r["type"], r["category"], r["amount"], r["description"] or "", r["created_at"]])
    return output.getvalue()


# ─────────────────────────────────────────────
# Budgets
# ─────────────────────────────────────────────

def set_category_budget(user_id: int, category: str, monthly_limit: float) -> None:
    """Create or update monthly budget for a category."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO budgets (user_id, category, monthly_limit)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, category)
               DO UPDATE SET monthly_limit = excluded.monthly_limit""",
            (user_id, category.strip().lower(), float(monthly_limit))
        )
        conn.commit()


def fetch_budgets(user_id: int) -> list[dict]:
    """Return all budget targets for a user."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category, monthly_limit FROM budgets WHERE user_id = ? ORDER BY monthly_limit DESC",
            (user_id,)
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_budget_vs_actual(user_id: int, start_date: str, end_date: str) -> list[dict]:
    """
    Compare configured budgets against actual expense spend for the period.
    Also includes categories with spend that don't have an explicit budget yet.
    """
    budgets = {b["category"]: b["monthly_limit"] for b in fetch_budgets(user_id)}
    spending = {s["category"]: s["total"] for s in fetch_spending_by_category(user_id, start_date, end_date)}

    all_categories = sorted(set(list(budgets.keys()) + list(spending.keys())))
    result = []
    for cat in all_categories:
        limit = budgets.get(cat, 0.0)
        spent = spending.get(cat, 0.0)
        percent = (spent / limit * 100) if limit > 0 else 0.0
        status = "safe"
        if limit > 0:
            if spent > limit:
                status = "exceeded"
            elif spent >= limit * 0.8:
                status = "warning"
        result.append({
            "category": cat,
            "monthly_limit": limit,
            "spent": spent,
            "percentage": round(percent, 1),
            "status": status,
        })
    return result


# ─────────────────────────────────────────────
# Chat Memory
# ─────────────────────────────────────────────

def store_message(user_id: int, role: str, message: str) -> None:
    """Persist a single chat turn."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_memory (user_id, role, message) VALUES (?, ?, ?)",
            (user_id, role, message)
        )
        conn.commit()


def fetch_chat_history(user_id: int, limit: int = 14) -> str:
    """Return recent chat history formatted oldest → newest."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT role, message
               FROM chat_memory
               WHERE user_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (user_id, limit)
        ).fetchall()

    rows = list(reversed(rows))
    return "\n".join(f"[{row['role']}] {row['message']}" for row in rows)


def clear_chat_memory(user_id: int) -> None:
    """Clear conversation history for the given user."""
    with get_connection() as conn:
        conn.execute("DELETE FROM chat_memory WHERE user_id = ?", (user_id,))
        conn.commit()


# ─────────────────────────────────────────────
# Financial Analytics & Health Metrics
# ─────────────────────────────────────────────

def fetch_financial_metrics(user_id: int) -> dict:
    """
    Computes deterministic financial metrics for AI agent and dashboard:
    - Current month income, expense, savings rate
    - 3-month averages
    - Top spending category
    - Budget adherence
    """
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    month_start = today.replace(day=1).isoformat()
    month_end = today.isoformat()

    with get_connection() as conn:
        # Current month totals
        cur_row = conn.execute(
            """SELECT
                   SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expense
               FROM transactions
               WHERE user_id = ? AND strftime('%Y-%m', date) = ?""",
            (user_id, current_month_str)
        ).fetchone()

        income = float(cur_row["income"] or 0)
        expense = float(cur_row["expense"] or 0)
        net_savings = income - expense
        savings_rate = round((net_savings / income * 100), 1) if income > 0 else 0.0

        # Category spending
        cat_rows = conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE user_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?
               GROUP BY category ORDER BY total DESC LIMIT 3""",
            (user_id, current_month_str)
        ).fetchall()

        top_categories = [{"category": r["category"], "total": float(r["total"])} for r in cat_rows]

        # Total transaction count
        count_row = conn.execute(
            "SELECT COUNT(*) as count FROM transactions WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        txn_count = count_row["count"] if count_row else 0

    budget_breakdown = fetch_budget_vs_actual(user_id, month_start, month_end)

    return {
        "current_month": current_month_str,
        "income": income,
        "expense": expense,
        "net_savings": net_savings,
        "savings_rate": savings_rate,
        "top_categories": top_categories,
        "transaction_count": txn_count,
        "budget_breakdown": budget_breakdown,
    }
