"""
app.py
------
Main entry point for the Personal Finance & Experience Tracker.
Handles DB initialization, recurring-transaction automation, cached data
loading (shared across all pages via st.session_state / cache), and the
sidebar landing page.
"""

import streamlit as st
import pandas as pd

import database as db
import helpers

st.set_page_config(
    page_title="Personal Finance & Experience Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------
# One-time setup: create DB tables if missing, run recurring automation
# --------------------------------------------------------------------------
db.init_db()

if "recurring_processed_today" not in st.session_state:
    created = helpers.process_recurring()
    st.session_state["recurring_processed_today"] = True
    if created > 0:
        st.toast(f"✅ Auto-added {created} recurring transaction(s) that were due today.")


# --------------------------------------------------------------------------
# PHASE 3: Cached data loader — shared by every page in this app.
# ttl=60 means the DB is hit at most once every 60 seconds per session.
# --------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_all_transactions() -> pd.DataFrame:
    """Fetches all transactions from SQLite and returns a typed Pandas DataFrame."""
    rows = db.fetch_all_transactions()
    return helpers.rows_to_dataframe(rows)


# --------------------------------------------------------------------------
# Landing page content
# --------------------------------------------------------------------------
st.title("💰 Personal Finance & Experience Tracker")

st.markdown(
    """
Welcome! Use the sidebar to navigate:

- **📥 Add Transaction** — log income or expenses with validation & smart auto-categorization
- **📊 Dashboard** — see balances, trends, and savings-goal progress at a glance
- **📈 Reports & Insights** — dig into your data, edit/delete entries, and export to CSV
- **⚙️ Settings & Goals** — manage budgets, auto-categorization rules, recurring transactions, and savings goals
"""
)

df = load_all_transactions()

# --------------------------------------------------------------------------
# Budget alerts in the SIDEBAR — visible on every page since app.py runs
# once per session and st.sidebar persists across page navigation.
# --------------------------------------------------------------------------
if not df.empty:
    sidebar_alerts = helpers.get_all_budget_alerts(df)
    if sidebar_alerts:
        st.sidebar.markdown("### ⚠️ Budget Alerts")
        for a in sidebar_alerts:
            st.sidebar.error(
                f"Over limit on **{a['category']}**\n\n"
                f"₹{a['spent']:,.0f} spent / ₹{a['limit']:,.0f} limit"
            )

# --------------------------------------------------------------------------
# Quick snapshot + budget alerts, visible from the landing page too
# --------------------------------------------------------------------------
if df.empty:
    st.info("No transactions yet. Head to **📥 Add Transaction** to get started!")
else:
    total_income = df.loc[df["type"] == "Income", "amount"].sum()
    total_expense = df.loc[df["type"] == "Expense", "amount"].sum()
    total_balance = total_income - total_expense

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Balance", f"₹{total_balance:,.0f}")
    col2.metric("Total Income (all-time)", f"₹{total_income:,.0f}")
    col3.metric("Total Expense (all-time)", f"₹{total_expense:,.0f}")

    alerts = helpers.get_all_budget_alerts(df)
    if alerts:
        st.markdown("---")
        for a in alerts:
            st.error(
                f"⚠️ BUDGET ALERT: Over limit on **{a['category']}** — "
                f"spent ₹{a['spent']:,.0f} of ₹{a['limit']:,.0f} this month!"
            )

st.markdown("---")
st.caption("Tip: your data is stored locally in `finance_tracker.db` (SQLite) next to this app.")
