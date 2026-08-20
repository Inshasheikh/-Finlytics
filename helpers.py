"""
helpers.py
----------
Validation logic, ETL / analytics functions, and auto-categorization
utilities for the Personal Finance & Experience Tracker.
"""

import re
from datetime import datetime, date
import pandas as pd

import database as db

DEFAULT_CATEGORIES = [
    "Food", "Rent", "Transport", "Salary", "Utilities", "Entertainment",
    "Shopping", "Health", "Education", "Savings", "Other",
]

PAYMENT_MODES = ["Cash", "UPI", "Credit Card", "Bank Transfer"]


# --------------------------------------------------------------------------
# PHASE 1: VALIDATION
# --------------------------------------------------------------------------
def validate_transaction(txn_date, amount, category, description, payment_mode):
    """
    Validates a transaction's raw form inputs.
    Returns (is_valid: bool, errors: list[str]).
    """
    errors = []

    # --- Date validation ---
    if txn_date is None:
        errors.append("Date is required.")
    else:
        if isinstance(txn_date, datetime):
            txn_date = txn_date.date()
        if txn_date > date.today():
            errors.append("Date cannot be in the future.")

    # --- Amount validation ---
    try:
        amount_val = float(amount)
        if amount_val <= 0:
            errors.append("Amount must be a positive number greater than 0.")
    except (TypeError, ValueError):
        errors.append("Amount must be a valid number.")

    # --- Category validation ---
    if not category or not str(category).strip():
        errors.append("Category must not be empty.")

    # --- Description validation ---
    if description and len(description) > 500:
        errors.append("Description must be 500 characters or fewer.")

    # --- Payment mode validation ---
    if not payment_mode or not str(payment_mode).strip():
        errors.append("Payment mode must be selected.")

    return (len(errors) == 0, errors)


def clean_text(text: str) -> str:
    """Strips excess whitespace and collapses multiple spaces using regex."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


# --------------------------------------------------------------------------
# AUTO-CATEGORIZATION
# --------------------------------------------------------------------------
def auto_categorize(description: str, fallback_category: str = None):
    """
    Scans the description against auto_rules keywords (case-insensitive,
    regex word-boundary aware) and returns the matching category.
    Falls back to `fallback_category` (usually the user-picked dropdown
    value) if no rule matches.
    """
    if not description:
        return fallback_category

    rules = db.fetch_all_rules()
    desc_lower = description.lower()

    for rule in rules:
        keyword = rule["keyword"].strip().lower()
        if not keyword:
            continue
        # Use regex search so partial-word matches like "swiggy's" still hit
        if re.search(re.escape(keyword), desc_lower):
            return rule["assigned_category"]

    return fallback_category


# --------------------------------------------------------------------------
# PHASE 3: DATA FETCHING (raw -> DataFrame). NOTE: the @st.cache_data
# decorator is applied where this is called from app.py / pages, since
# helpers.py is meant to stay Streamlit-agnostic and easily testable.
# --------------------------------------------------------------------------
def rows_to_dataframe(rows) -> pd.DataFrame:
    """Converts a list of sqlite3.Row objects from `transactions` into a typed DataFrame."""
    columns = [
        "id", "date", "amount", "category", "description",
        "payment_mode", "type", "is_recurring", "created_at",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame([dict(row) for row in rows])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    return df


# --------------------------------------------------------------------------
# PHASE 4: DATA TRANSFORMATION (ETL for analytics)
# --------------------------------------------------------------------------
def get_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups transactions by month and returns Income, Expense, and Net
    Savings totals per month.
    """
    if df.empty:
        return pd.DataFrame(columns=["month", "Income", "Expense", "Net Savings"])

    grouped = (
        df.groupby([pd.Grouper(key="date", freq="ME"), "type"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    grouped = grouped.rename(columns={"date": "month"})

    for col in ["Income", "Expense"]:
        if col not in grouped.columns:
            grouped[col] = 0.0

    grouped["Net Savings"] = grouped["Income"] - grouped["Expense"]
    return grouped


def get_category_breakdown(df: pd.DataFrame, month: int = None, year: int = None) -> pd.DataFrame:
    """
    Sums expense amounts per category for the given month/year
    (defaults to the current month).
    """
    if df.empty:
        return pd.DataFrame(columns=["category", "amount"])

    today = date.today()
    month = month or today.month
    year = year or today.year

    mask = (
        (df["type"] == "Expense")
        & (df["date"].dt.month == month)
        & (df["date"].dt.year == year)
    )
    subset = df[mask]
    if subset.empty:
        return pd.DataFrame(columns=["category", "amount"])

    breakdown = subset.groupby("category", as_index=False)["amount"].sum()
    breakdown = breakdown.sort_values("amount", ascending=False)
    return breakdown


def calculate_running_balance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sorts by date and adds a cumulative running-balance column
    (Income adds, Expense subtracts).
    """
    if df.empty:
        result = df.copy()
        result["signed_amount"] = pd.Series(dtype=float)
        result["running_balance"] = pd.Series(dtype=float)
        return result

    result = df.sort_values("date").copy()
    result["signed_amount"] = result.apply(
        lambda row: row["amount"] if row["type"] == "Income" else -row["amount"], axis=1
    )
    result["running_balance"] = result["signed_amount"].cumsum()
    return result


def compare_with_budget(df: pd.DataFrame, category: str, month: int = None, year: int = None):
    """
    Fetches the budget limit for `category` and compares it against the
    actual expense total for the given month/year.
    Returns dict: {limit, spent, over_budget, remaining} or None if no budget set.
    """
    limit = db.get_budget_for_category(category)
    if limit is None:
        return None

    today = date.today()
    month = month or today.month
    year = year or today.year

    if df.empty:
        spent = 0.0
    else:
        mask = (
            (df["type"] == "Expense")
            & (df["category"] == category)
            & (df["date"].dt.month == month)
            & (df["date"].dt.year == year)
        )
        spent = df.loc[mask, "amount"].sum()

    return {
        "limit": limit,
        "spent": spent,
        "over_budget": spent > limit,
        "remaining": limit - spent,
    }


def get_all_budget_alerts(df: pd.DataFrame) -> list:
    """Returns a list of category names that are currently over their monthly budget."""
    budgets = db.fetch_all_budgets()
    alerts = []
    for b in budgets:
        result = compare_with_budget(df, b["category"])
        if result and result["over_budget"]:
            alerts.append({
                "category": b["category"],
                "spent": result["spent"],
                "limit": result["limit"],
            })
    return alerts


# --------------------------------------------------------------------------
# PHASE 5: TEXT INSIGHTS (Auto-Analysis)
# --------------------------------------------------------------------------
def generate_text_insights(df: pd.DataFrame) -> list:
    """
    Generates a list of human-readable insight strings from the
    transactions DataFrame, comparing this month to last month and
    surfacing the largest single expense.
    """
    insights = []
    if df.empty:
        return ["No transactions yet — add your first entry to see insights here."]

    today = date.today()
    this_month, this_year = today.month, today.year
    last_month_date = (pd.Timestamp(today.year, today.month, 1) - pd.DateOffset(months=1))
    last_month, last_year = last_month_date.month, last_month_date.year

    expenses = df[df["type"] == "Expense"]

    # --- Category month-over-month comparison ---
    this_month_cat = expenses[
        (expenses["date"].dt.month == this_month) & (expenses["date"].dt.year == this_year)
    ].groupby("category")["amount"].sum()

    last_month_cat = expenses[
        (expenses["date"].dt.month == last_month) & (expenses["date"].dt.year == last_year)
    ].groupby("category")["amount"].sum()

    for category, this_amt in this_month_cat.items():
        last_amt = last_month_cat.get(category, 0)
        if last_amt > 0:
            pct_change = ((this_amt - last_amt) / last_amt) * 100
            if abs(pct_change) >= 1:
                direction = "higher" if pct_change > 0 else "lower"
                insights.append(
                    f"This month you spent ₹{this_amt:,.0f} on {category}, "
                    f"which is {abs(pct_change):.0f}% {direction} than last month."
                )
        elif this_amt > 0:
            insights.append(
                f"This month you spent ₹{this_amt:,.0f} on {category}, a new category vs. last month."
            )

    # --- Highest single expense ---
    if not expenses.empty:
        top_row = expenses.loc[expenses["amount"].idxmax()]
        insights.append(
            f"Your highest single expense was ₹{top_row['amount']:,.0f} on "
            f"{top_row['date'].strftime('%d %b %Y')} for {top_row['description'] or top_row['category']}."
        )

    # --- Overall savings rate this month ---
    income_this_month = df[
        (df["type"] == "Income") & (df["date"].dt.month == this_month) & (df["date"].dt.year == this_year)
    ]["amount"].sum()
    expense_this_month = this_month_cat.sum() if not this_month_cat.empty else 0
    if income_this_month > 0:
        savings_rate = ((income_this_month - expense_this_month) / income_this_month) * 100
        insights.append(f"Your savings rate this month is {savings_rate:.0f}% of income.")

    if not insights:
        insights.append("Not enough data yet for month-over-month comparisons.")

    return insights


def get_weekday_heatmap_data(df: pd.DataFrame) -> pd.DataFrame:
    """Returns expense totals grouped by weekday, ordered Monday -> Sunday."""
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if df.empty:
        return pd.DataFrame({"weekday": weekday_order, "amount": [0] * 7})

    expenses = df[df["type"] == "Expense"].copy()
    if expenses.empty:
        return pd.DataFrame({"weekday": weekday_order, "amount": [0] * 7})

    expenses["weekday"] = expenses["date"].dt.day_name()
    grouped = expenses.groupby("weekday")["amount"].sum().reindex(weekday_order, fill_value=0)
    return grouped.reset_index()


# --------------------------------------------------------------------------
# RECURRING TRANSACTIONS AUTOMATION
# --------------------------------------------------------------------------
def _advance_date(date_str: str, frequency: str) -> str:
    """Given an ISO date string, returns the next occurrence based on frequency."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    if frequency == "Monthly":
        # Add one month, handling year rollover and day-of-month overflow
        month = d.month + 1
        year = d.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        day = min(d.day, _days_in_month(year, month))
        new_date = date(year, month, day)
    else:  # Yearly
        try:
            new_date = d.replace(year=d.year + 1)
        except ValueError:
            # Feb 29 on a non-leap year
            new_date = d.replace(year=d.year + 1, day=28)
    return new_date.isoformat()


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


def process_recurring():
    """
    Checks all recurring_transactions. For any entry whose next_due_date
    is today or earlier, inserts a new transaction and advances the
    next_due_date. Returns the number of transactions created.
    """
    today_str = date.today().isoformat()
    created_count = 0

    try:
        recurring_entries = db.fetch_all_recurring()
        for entry in recurring_entries:
            if entry["next_due_date"] <= today_str:
                txn_data = {
                    "date": entry["next_due_date"],
                    "amount": entry["amount"],
                    "category": entry["category"],
                    "description": f"[Recurring] {entry['description'] or ''}".strip(),
                    "payment_mode": entry["payment_mode"],
                    "type": entry["type"],
                    "is_recurring": 1,
                }
                success = db.add_transaction(txn_data)
                if success:
                    created_count += 1
                    new_due_date = _advance_date(entry["next_due_date"], entry["frequency"])
                    db.update_recurring_next_due_date(entry["id"], new_due_date)
    except Exception as e:
        print(f"[ERROR] process_recurring failed: {e}")

    return created_count
