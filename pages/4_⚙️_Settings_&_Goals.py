"""
pages/4_⚙️_Settings_&_Goals.py
--------------------------------
Manage budgets, auto-categorization rules, recurring transactions,
and savings goals.
"""

import streamlit as st
from datetime import date

import database as db
import helpers

st.set_page_config(page_title="Settings & Goals", page_icon="⚙️", layout="wide")
st.title("⚙️ Settings & Goals")

tab_budgets, tab_rules, tab_recurring, tab_goals = st.tabs(
    ["💰 Budgets", "🤖 Auto-Categorization", "🔁 Recurring Transactions", "🎯 Savings Goals"]
)

# --------------------------------------------------------------------------
# TAB 1: Budgets
# --------------------------------------------------------------------------
with tab_budgets:
    st.subheader("Monthly Budgets per Category")
    st.caption("Set a monthly spending limit for any category. You'll get alerts when you go over.")

    with st.form("budget_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            budget_category = st.selectbox("Category", helpers.DEFAULT_CATEGORIES)
        with col2:
            budget_limit = st.number_input("Monthly Limit (₹)", min_value=0.0, step=100.0)
        budget_submit = st.form_submit_button("💾 Save Budget")

    if budget_submit:
        if budget_limit <= 0:
            st.error("❌ Monthly limit must be greater than 0.")
        else:
            if db.upsert_budget(budget_category, float(budget_limit)):
                st.success(f"✅ Budget for {budget_category} set to ₹{budget_limit:,.0f}/month.")
                st.rerun()
            else:
                st.error("❌ Failed to save budget.")

    st.markdown("---")
    existing_budgets = db.fetch_all_budgets()
    if existing_budgets:
        for b in existing_budgets:
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(f"**{b['category']}**")
            c2.write(f"₹{b['monthly_limit']:,.0f} / month")
            if c3.button("🗑️ Remove", key=f"del_budget_{b['id']}"):
                db.delete_budget(b["id"])
                st.rerun()
    else:
        st.caption("No budgets set yet.")

# --------------------------------------------------------------------------
# TAB 2: Auto-Categorization Rules
# --------------------------------------------------------------------------
with tab_rules:
    st.subheader("Smart Auto-Categorization Rules")
    st.caption(
        "If a transaction description contains the keyword, it will automatically be "
        "assigned to the linked category (e.g., 'Swiggy' → 'Food')."
    )

    with st.form("rule_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            keyword = st.text_input("Keyword (e.g., Swiggy, Uber, Netflix)")
        with col2:
            rule_category = st.selectbox("Assign to category", helpers.DEFAULT_CATEGORIES, key="rule_cat")
        rule_submit = st.form_submit_button("➕ Add Rule")

    if rule_submit:
        if not keyword.strip():
            st.error("❌ Keyword cannot be empty.")
        else:
            if db.add_auto_rule(keyword, rule_category):
                st.success(f"✅ Rule added: '{keyword}' → {rule_category}")
                st.rerun()
            else:
                st.error("❌ Failed to add rule.")

    st.markdown("---")
    existing_rules = db.fetch_all_rules()
    if existing_rules:
        for r in existing_rules:
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.write(f"**{r['keyword']}**")
            c2.write(f"→ {r['assigned_category']}")
            if c3.button("🗑️", key=f"del_rule_{r['id']}"):
                db.delete_auto_rule(r["id"])
                st.rerun()
    else:
        st.caption("No auto-categorization rules yet.")

# --------------------------------------------------------------------------
# TAB 3: Recurring Transactions
# --------------------------------------------------------------------------
with tab_recurring:
    st.subheader("Recurring Transactions")
    st.caption(
        "Set up transactions that repeat automatically (e.g., Rent every month). "
        "They'll be added to your transactions log on their due date, next time you open the app."
    )

    with st.form("recurring_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            rec_description = st.text_input("Description (e.g., Rent, Netflix Subscription)")
            rec_type = st.selectbox("Type", ["Expense", "Income"], key="rec_type")
        with col2:
            rec_amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, key="rec_amount")
            rec_category = st.selectbox("Category", helpers.DEFAULT_CATEGORIES, key="rec_cat")
        with col3:
            rec_payment_mode = st.selectbox("Payment Mode", helpers.PAYMENT_MODES, key="rec_pm")
            rec_frequency = st.selectbox("Frequency", ["Monthly", "Yearly"])

        rec_next_due = st.date_input("Next Due Date", value=date.today())
        rec_submit = st.form_submit_button("➕ Add Recurring Transaction")

    if rec_submit:
        if rec_amount <= 0:
            st.error("❌ Amount must be greater than 0.")
        else:
            rec_data = {
                "description": helpers.clean_text(rec_description),
                "amount": float(rec_amount),
                "category": rec_category,
                "payment_mode": rec_payment_mode,
                "frequency": rec_frequency,
                "next_due_date": rec_next_due.isoformat(),
                "type": rec_type,
            }
            if db.add_recurring_transaction(rec_data):
                st.success("✅ Recurring transaction scheduled!")
                st.rerun()
            else:
                st.error("❌ Failed to schedule recurring transaction.")

    st.markdown("---")
    existing_recurring = db.fetch_all_recurring()
    if existing_recurring:
        for rec in existing_recurring:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(f"**{rec['description'] or rec['category']}** ({rec['type']})")
            c2.write(f"₹{rec['amount']:,.0f} · {rec['frequency']}")
            c3.write(f"Next: {rec['next_due_date']}")
            if c4.button("🗑️", key=f"del_rec_{rec['id']}"):
                db.delete_recurring_transaction(rec["id"])
                st.rerun()
    else:
        st.caption("No recurring transactions set up yet.")

# --------------------------------------------------------------------------
# TAB 4: Savings Goals
# --------------------------------------------------------------------------
with tab_goals:
    st.subheader("Savings Goals")

    with st.form("goal_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            goal_name = st.text_input("Goal Name (e.g., Vacation, Emergency Fund)")
        with col2:
            goal_target = st.number_input("Target Amount (₹)", min_value=0.0, step=1000.0)
        with col3:
            goal_deadline = st.date_input("Deadline", value=date.today())
        goal_submit = st.form_submit_button("🎯 Create Goal")

    if goal_submit:
        if not goal_name.strip():
            st.error("❌ Goal name cannot be empty.")
        elif goal_target <= 0:
            st.error("❌ Target amount must be greater than 0.")
        else:
            if db.add_savings_goal(goal_name.strip(), float(goal_target), goal_deadline.isoformat()):
                st.success(f"✅ Goal '{goal_name}' created!")
                st.rerun()
            else:
                st.error("❌ Failed to create goal.")

    st.markdown("---")
    existing_goals = db.fetch_all_goals()
    if existing_goals:
        for g in existing_goals:
            with st.container(border=True):
                pct = min((g["current_saved"] / g["target_amount"]) * 100, 100) if g["target_amount"] > 0 else 0
                st.write(f"**{g['goal_name']}** — Deadline: {g['deadline']}")
                st.progress(int(pct))
                st.caption(f"₹{g['current_saved']:,.0f} / ₹{g['target_amount']:,.0f} ({pct:.0f}%)")

                add_col, del_col = st.columns([3, 1])
                with add_col:
                    add_amount = st.number_input(
                        "Add savings amount (₹)", min_value=0.0, step=100.0, key=f"add_amt_{g['id']}"
                    )
                    if st.button("💰 Add Savings", key=f"add_save_{g['id']}"):
                        if add_amount > 0:
                            # Record as a manual Income transaction categorized as "Savings"
                            txn_data = {
                                "date": date.today().isoformat(),
                                "amount": float(add_amount),
                                "category": "Savings",
                                "description": f"Contribution to goal: {g['goal_name']}",
                                "payment_mode": "Bank Transfer",
                                "type": "Income",
                                "is_recurring": 0,
                            }
                            db.add_transaction(txn_data)
                            db.add_to_savings_goal(g["id"], float(add_amount))
                            st.cache_data.clear()
                            st.success("✅ Savings added!")
                            st.rerun()
                        else:
                            st.error("❌ Enter an amount greater than 0.")
                with del_col:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Delete Goal", key=f"del_goal_{g['id']}"):
                        db.delete_savings_goal(g["id"])
                        st.rerun()
    else:
        st.caption("No savings goals yet. Create one above!")
