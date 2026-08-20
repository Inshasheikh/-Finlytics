"""
pages/3_📈_Reports_&_Insights.py
----------------------------------
Phase 6: raw data table with per-row Edit / Delete, CSV export, plus
running balance and budget-vs-actual views.
"""

import streamlit as st
import pandas as pd
from datetime import date

import database as db
import helpers

st.set_page_config(page_title="Reports & Insights", page_icon="📈", layout="wide")
st.title("📈 Reports & Insights")


@st.cache_data(ttl=60)
def load_all_transactions() -> pd.DataFrame:
    rows = db.fetch_all_transactions()
    return helpers.rows_to_dataframe(rows)


df = load_all_transactions()

if df.empty:
    st.info("No data available yet. Add a transaction first.")
    st.stop()

# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------
with st.expander("🔍 Filters", expanded=True):
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        type_filter = st.multiselect("Type", ["Income", "Expense"], default=["Income", "Expense"])
    with fcol2:
        cat_options = sorted(df["category"].dropna().unique().tolist())
        cat_filter = st.multiselect("Category", cat_options, default=cat_options)
    with fcol3:
        date_range = st.date_input(
            "Date range",
            value=(df["date"].min().date(), df["date"].max().date()),
        )

filtered_df = df[df["type"].isin(type_filter) & df["category"].isin(cat_filter)]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    filtered_df = filtered_df[
        (filtered_df["date"].dt.date >= start) & (filtered_df["date"].dt.date <= end)
    ]

st.markdown("---")

# --------------------------------------------------------------------------
# Raw data table
# --------------------------------------------------------------------------
st.subheader("📋 Transaction Records")

if filtered_df.empty:
    st.warning("No transactions match the selected filters.")
else:
    display_df = filtered_df.copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(
        display_df[["id", "date", "type", "category", "amount", "payment_mode", "description"]],
        use_container_width=True,
        hide_index=True,
    )

    # --- Export ---
    csv_bytes = display_df[
        ["id", "date", "type", "category", "amount", "payment_mode", "description"]
    ].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Export filtered data to CSV",
        data=csv_bytes,
        file_name=f"transactions_{date.today().isoformat()}.csv",
        mime="text/csv",
    )

st.markdown("---")

# --------------------------------------------------------------------------
# Edit / Delete per row
# --------------------------------------------------------------------------
st.subheader("✏️ Edit or 🗑️ Delete a Transaction")

if filtered_df.empty:
    st.caption("Nothing to edit — adjust your filters or add a transaction.")
else:
    txn_options = {
        f"#{row['id']} · {row['date'].strftime('%Y-%m-%d')} · {row['category']} · ₹{row['amount']:,.0f}": row["id"]
        for _, row in filtered_df.iterrows()
    }
    selected_label = st.selectbox("Select a transaction", list(txn_options.keys()))
    selected_id = txn_options[selected_label]
    selected_row = filtered_df[filtered_df["id"] == selected_id].iloc[0]

    edit_col, delete_col = st.columns(2)

    # --- EDIT ---
    with edit_col:
        st.markdown("**Edit this transaction**")
        with st.form(f"edit_form_{selected_id}"):
            new_date = st.date_input("Date", value=selected_row["date"].date(), max_value=date.today())
            new_amount = st.number_input("Amount (₹)", min_value=0.0, value=float(selected_row["amount"]), step=10.0)
            new_category = st.selectbox(
                "Category",
                options=helpers.DEFAULT_CATEGORIES,
                index=helpers.DEFAULT_CATEGORIES.index(selected_row["category"])
                if selected_row["category"] in helpers.DEFAULT_CATEGORIES else 0,
            )
            new_description = st.text_area(
                "Description", value=selected_row["description"] or "", max_chars=500
            )
            new_payment_mode = st.selectbox(
                "Payment Mode", helpers.PAYMENT_MODES,
                index=helpers.PAYMENT_MODES.index(selected_row["payment_mode"])
                if selected_row["payment_mode"] in helpers.PAYMENT_MODES else 0,
            )
            new_type = st.selectbox(
                "Type", ["Income", "Expense"],
                index=0 if selected_row["type"] == "Income" else 1,
            )

            update_submitted = st.form_submit_button("💾 Save Changes")

        if update_submitted:
            is_valid, errors = helpers.validate_transaction(
                new_date, new_amount, new_category, new_description, new_payment_mode
            )
            if not is_valid:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                updated_data = {
                    "date": new_date.isoformat(),
                    "amount": float(new_amount),
                    "category": new_category,
                    "description": helpers.clean_text(new_description),
                    "payment_mode": new_payment_mode,
                    "type": new_type,
                    "is_recurring": int(selected_row["is_recurring"]),
                }
                if db.update_transaction(int(selected_id), updated_data):
                    st.success("✅ Transaction updated successfully!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Failed to update transaction.")

    # --- DELETE ---
    with delete_col:
        st.markdown("**Delete this transaction**")
        st.write(f"You are about to delete transaction **#{selected_id}**:")
        st.write(
            f"{selected_row['date'].strftime('%Y-%m-%d')} · {selected_row['category']} · "
            f"₹{selected_row['amount']:,.0f} · {selected_row['description']}"
        )
        confirm_delete = st.checkbox("I confirm I want to permanently delete this transaction.", key=f"confirm_{selected_id}")
        if st.button("🗑️ Delete Transaction", disabled=not confirm_delete, use_container_width=True):
            if db.delete_transaction(int(selected_id)):
                st.success("✅ Transaction deleted.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("❌ Failed to delete transaction.")

st.markdown("---")

# --------------------------------------------------------------------------
# Running balance
# --------------------------------------------------------------------------
st.subheader("💹 Running Balance Over Time")
balance_df = helpers.calculate_running_balance(df)
if balance_df.empty:
    st.caption("No data available.")
else:
    import plotly.express as px
    fig = px.line(
        balance_df, x="date", y="running_balance",
        template="plotly_dark", labels={"running_balance": "Balance (₹)", "date": "Date"},
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --------------------------------------------------------------------------
# Budget vs actual
# --------------------------------------------------------------------------
st.subheader("🎯 Budget vs Actual (This Month)")
budgets = db.fetch_all_budgets()
if not budgets:
    st.caption("No budgets configured yet. Set them in ⚙️ Settings & Goals.")
else:
    rows = []
    for b in budgets:
        result = helpers.compare_with_budget(df, b["category"])
        if result:
            rows.append({
                "Category": b["category"],
                "Budget": result["limit"],
                "Spent": result["spent"],
                "Remaining": result["remaining"],
                "Status": "⚠️ Over Budget" if result["over_budget"] else "✅ On Track",
            })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
