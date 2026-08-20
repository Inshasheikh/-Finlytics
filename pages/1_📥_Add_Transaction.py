"""
pages/1_📥_Add_Transaction.py
------------------------------
Phase 1 & 2: user input form with validation, then insert into SQLite.
"""

import streamlit as st
from datetime import date

import database as db
import helpers

st.set_page_config(page_title="Add Transaction", page_icon="📥", layout="wide")
st.title("📥 Add Transaction")

with st.form("add_transaction_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        txn_date = st.date_input("Date", value=date.today(), max_value=date.today())
        amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0, format="%.2f")
        txn_type = st.selectbox("Type", ["Expense", "Income"])

    with col2:
        category = st.selectbox(
            "Category",
            options=helpers.DEFAULT_CATEGORIES,
        )
        custom_category = st.text_input(
            "Or type a new category (overrides dropdown if filled)"
        )

        payment_mode = st.selectbox("Payment Mode", helpers.PAYMENT_MODES)

    description = st.text_area("Description (max 500 characters)", max_chars=500, height=100)
    is_recurring = st.checkbox("Mark as recurring (informational only — use Settings to automate)")

    submitted = st.form_submit_button("➕ Add Transaction", use_container_width=True)

if submitted:
    final_category = custom_category.strip() if custom_category.strip() else category

    # --- Phase 1: Validation ---
    is_valid, errors = helpers.validate_transaction(
        txn_date, amount, final_category, description, payment_mode
    )

    if not is_valid:
        for err in errors:
            st.error(f"❌ {err}")
        st.stop()

    # --- Auto-categorization can override the picked category based on description keywords ---
    resolved_category = helpers.auto_categorize(description, fallback_category=final_category)
    if resolved_category != final_category:
        st.info(f"🤖 Auto-categorized as **{resolved_category}** based on your description.")

    txn_dict = {
        "date": txn_date.isoformat(),
        "amount": float(amount),
        "category": resolved_category,
        "description": helpers.clean_text(description),
        "payment_mode": payment_mode,
        "type": txn_type,
        "is_recurring": int(is_recurring),
    }

    # --- Phase 2: Insert into DB ---
    success = db.add_transaction(txn_dict)
    if success:
        st.success("✅ Transaction Added Successfully!")
        st.cache_data.clear()  # invalidate cached load_all_transactions so other pages see it
        st.balloons()
    else:
        st.error("❌ Failed to add transaction. Please check the logs and try again.")

st.markdown("---")
st.subheader("Recently Added")
recent_rows = db.fetch_all_transactions()[:5]
if recent_rows:
    recent_df = helpers.rows_to_dataframe(recent_rows)[
        ["date", "amount", "category", "type", "payment_mode", "description"]
    ]
    st.dataframe(recent_df, use_container_width=True, hide_index=True)
else:
    st.caption("No transactions yet.")
