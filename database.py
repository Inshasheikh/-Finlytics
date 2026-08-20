"""
database.py
-----------
All SQLite database operations for the Personal Finance & Experience Tracker.
Contains schema creation and CRUD functions for every table.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finance_tracker.db")


# --------------------------------------------------------------------------
# Connection helper
# --------------------------------------------------------------------------
@contextmanager
def get_connection():
    """
    Context manager that yields a sqlite3 connection with foreign keys
    enabled and commits/rolls back automatically.
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DB ERROR] Transaction rolled back: {e}")
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Schema initialization
# --------------------------------------------------------------------------
def init_db():
    """
    Creates the SQLite database file (if it doesn't exist) and all
    required tables. Safe to call on every app startup.
    """
    try:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL CHECK (amount > 0),
                    category TEXT NOT NULL,
                    description TEXT,
                    payment_mode TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('Income', 'Expense')),
                    is_recurring INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT UNIQUE NOT NULL,
                    monthly_limit REAL NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS auto_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    assigned_category TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS recurring_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    payment_mode TEXT NOT NULL,
                    frequency TEXT NOT NULL CHECK (frequency IN ('Monthly', 'Yearly')),
                    next_due_date TEXT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('Income', 'Expense'))
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS savings_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    current_saved REAL DEFAULT 0,
                    deadline TEXT
                )
            """)
    except Exception as e:
        print(f"[DB ERROR] Failed to initialize database: {e}")
        raise


# --------------------------------------------------------------------------
# TRANSACTIONS - CRUD
# --------------------------------------------------------------------------
def add_transaction(data: dict) -> bool:
    """
    Inserts a validated transaction dict into the transactions table.
    Expected keys: date, amount, category, description, payment_mode, type, is_recurring
    Returns True on success, False on failure.
    """
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO transactions
                    (date, amount, category, description, payment_mode, type, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["date"],
                    data["amount"],
                    data["category"],
                    data.get("description", ""),
                    data["payment_mode"],
                    data["type"],
                    int(data.get("is_recurring", 0)),
                ),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] add_transaction failed: {e}")
        return False


def fetch_all_transactions() -> list:
    """Returns all transactions as a list of sqlite3.Row objects (raw, uncached)."""
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC")
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] fetch_all_transactions failed: {e}")
        return []


def update_transaction(txn_id: int, data: dict) -> bool:
    """Updates an existing transaction by id."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE transactions
                SET date = ?, amount = ?, category = ?, description = ?,
                    payment_mode = ?, type = ?, is_recurring = ?
                WHERE id = ?
                """,
                (
                    data["date"],
                    data["amount"],
                    data["category"],
                    data.get("description", ""),
                    data["payment_mode"],
                    data["type"],
                    int(data.get("is_recurring", 0)),
                    txn_id,
                ),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] update_transaction failed: {e}")
        return False


def delete_transaction(txn_id: int) -> bool:
    """Deletes a transaction by id."""
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        return True
    except Exception as e:
        print(f"[DB ERROR] delete_transaction failed: {e}")
        return False


# --------------------------------------------------------------------------
# BUDGETS
# --------------------------------------------------------------------------
def upsert_budget(category: str, monthly_limit: float) -> bool:
    """Inserts a new budget or updates the limit if the category already exists."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO budgets (category, monthly_limit)
                VALUES (?, ?)
                ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit
                """,
                (category, monthly_limit),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] upsert_budget failed: {e}")
        return False


def fetch_all_budgets() -> list:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM budgets ORDER BY category")
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] fetch_all_budgets failed: {e}")
        return []


def get_budget_for_category(category: str):
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT monthly_limit FROM budgets WHERE category = ?", (category,))
            row = cur.fetchone()
            return row["monthly_limit"] if row else None
    except Exception as e:
        print(f"[DB ERROR] get_budget_for_category failed: {e}")
        return None


def delete_budget(budget_id: int) -> bool:
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        return True
    except Exception as e:
        print(f"[DB ERROR] delete_budget failed: {e}")
        return False


# --------------------------------------------------------------------------
# AUTO-CATEGORIZATION RULES
# --------------------------------------------------------------------------
def add_auto_rule(keyword: str, category: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO auto_rules (keyword, assigned_category) VALUES (?, ?)",
                (keyword.strip(), category.strip()),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] add_auto_rule failed: {e}")
        return False


def fetch_all_rules() -> list:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM auto_rules ORDER BY keyword")
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] fetch_all_rules failed: {e}")
        return []


def delete_auto_rule(rule_id: int) -> bool:
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM auto_rules WHERE id = ?", (rule_id,))
        return True
    except Exception as e:
        print(f"[DB ERROR] delete_auto_rule failed: {e}")
        return False


# --------------------------------------------------------------------------
# RECURRING TRANSACTIONS
# --------------------------------------------------------------------------
def add_recurring_transaction(data: dict) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO recurring_transactions
                    (description, amount, category, payment_mode, frequency, next_due_date, type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("description", ""),
                    data["amount"],
                    data["category"],
                    data["payment_mode"],
                    data["frequency"],
                    data["next_due_date"],
                    data["type"],
                ),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] add_recurring_transaction failed: {e}")
        return False


def fetch_all_recurring() -> list:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM recurring_transactions ORDER BY next_due_date")
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] fetch_all_recurring failed: {e}")
        return []


def update_recurring_next_due_date(rec_id: int, new_date: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE recurring_transactions SET next_due_date = ? WHERE id = ?",
                (new_date, rec_id),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] update_recurring_next_due_date failed: {e}")
        return False


def delete_recurring_transaction(rec_id: int) -> bool:
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM recurring_transactions WHERE id = ?", (rec_id,))
        return True
    except Exception as e:
        print(f"[DB ERROR] delete_recurring_transaction failed: {e}")
        return False


# --------------------------------------------------------------------------
# SAVINGS GOALS
# --------------------------------------------------------------------------
def add_savings_goal(goal_name: str, target_amount: float, deadline: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO savings_goals (goal_name, target_amount, current_saved, deadline)
                VALUES (?, ?, 0, ?)
                """,
                (goal_name, target_amount, deadline),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] add_savings_goal failed: {e}")
        return False


def fetch_all_goals() -> list:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM savings_goals ORDER BY deadline")
            return cur.fetchall()
    except Exception as e:
        print(f"[DB ERROR] fetch_all_goals failed: {e}")
        return []


def add_to_savings_goal(goal_id: int, amount: float) -> bool:
    """Increments current_saved for a goal by the given amount."""
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE savings_goals SET current_saved = current_saved + ? WHERE id = ?",
                (amount, goal_id),
            )
        return True
    except Exception as e:
        print(f"[DB ERROR] add_to_savings_goal failed: {e}")
        return False


def delete_savings_goal(goal_id: int) -> bool:
    try:
        with get_connection() as conn:
            conn.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
        return True
    except Exception as e:
        print(f"[DB ERROR] delete_savings_goal failed: {e}")
        return False
