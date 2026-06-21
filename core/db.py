"""
core/db.py
Database layer for FinBuddy.

Design decisions:
- Plain sqlite3 (no ORM overhead for a portfolio project; shows you understand SQL)
- Transactions stored as normalized columns, not a JSON blob
- Passwords stored as bcrypt hashes (never plaintext)
- Every connection opened and closed within each function (safe for FastAPI's thread pool)
"""

import sqlite3
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Allow override via env var so tests can use an in-memory DB
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finbuddy.db")

# Strip the sqlite:/// prefix to get the file path
DB_PATH = DATABASE_URL.replace("sqlite:///", "")


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────

def setup_database() -> None:
    """Create all tables if they don't exist. Safe to call on every startup."""
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

            CREATE TABLE IF NOT EXISTS chat_memory (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('user', 'bot')),
                message     TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            -- Index for fast per-user transaction queries
            CREATE INDEX IF NOT EXISTS idx_transactions_user_date
                ON transactions(user_id, date);

            -- Index for fast chat history lookup
            CREATE INDEX IF NOT EXISTS idx_chat_memory_user
                ON chat_memory(user_id, id);
        """)


# ─────────────────────────────────────────────
# User Management
# ─────────────────────────────────────────────

def create_user(username: str, pin_hash: str) -> int:
    """
    Insert a new user. Raises sqlite3.IntegrityError if username already exists.
    Returns the new user's id.
    """
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
    """
    Insert a transaction with proper normalized columns.
    Returns the new transaction id.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO transactions (user_id, date, amount, type, category, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, date, amount, type_.lower(), category.lower(), description)
        )
        conn.commit()
        return cursor.lastrowid


def fetch_recent_transactions(user_id: int, limit: int = 10) -> list[dict]:
    """Return the most recent N transactions for a user as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT date, amount, type, category, description
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
            """SELECT date, amount, type, category, description
               FROM transactions
               WHERE user_id = ? AND date BETWEEN ? AND ?
               ORDER BY date DESC""",
            (user_id, start_date, end_date)
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_spending_by_category(user_id: int, start_date: str, end_date: str) -> list[dict]:
    """
    Return total spending per category for a date range.
    Used to render the doughnut/bar chart on the dashboard.
    """
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
    """
    Return month-by-month income vs expense totals.
    Used to render the trend line chart.
    """
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


def fetch_chat_history(user_id: int, limit: int = 12) -> str:
    """
    Return chat history as a plain string (oldest → newest).
    The LLM prompt receives this as context.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT role, message
               FROM chat_memory
               WHERE user_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (user_id, limit)
        ).fetchall()

    # Reverse so it's oldest → newest
    rows = list(reversed(rows))
    return "\n".join(f"[{row['role']}] {row['message']}" for row in rows)
