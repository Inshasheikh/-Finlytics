"""
pages/2_📊_Dashboard.py
------------------------
Phase 5: metric cards, trend chart, category pie chart, weekday heatmap,
budget alerts, and savings-goal progress bars.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

import database as db
import helpers

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")


@st.cache_data(ttl=60)
def load_all_transactions() -> pd.DataFrame:
    rows = db.fetch_all_transactions()
    return helpers.rows_to_dataframe(rows)


df = load_all_transactions()

if df.empty:
    st.info("No data available yet. Add a transaction to see your dashboard come to life.")
    st.stop()

# --- Budget alerts in the sidebar (each page runs independently in Streamlit) ---
sidebar_alerts = helpers.get_all_budget_alerts(df)
if sidebar_alerts:
    st.sidebar.markdown("### ⚠️ Budget Alerts")
    for a in sidebar_alerts:
        st.sidebar.error(
            f"Over limit on **{a['category']}**\n\n"
            f"₹{a['spent']:,.0f} spent / ₹{a['limit']:,.0f} limit"
        )

today = date.today()

# --------------------------------------------------------------------------
# Budget alerts (prominent, at the top)
# --------------------------------------------------------------------------
alerts = helpers.get_all_budget_alerts(df)
if alerts:
    for a in alerts:
        st.error(
            f"⚠️ BUDGET ALERT: Over limit on **{a['category']}** — "
            f"spent ₹{a['spent']:,.0f} of ₹{a['limit']:,.0f} this month!"
        )

# --------------------------------------------------------------------------
# D. Metric cards
# --------------------------------------------------------------------------
total_income_all = df.loc[df["type"] == "Income", "amount"].sum()
total_expense_all = df.loc[df["type"] == "Expense", "amount"].sum()
total_balance = total_income_all - total_expense_all

this_month_df = df[(df["date"].dt.month == today.month) & (df["date"].dt.year == today.year)]
monthly_income = this_month_df.loc[this_month_df["type"] == "Income", "amount"].sum()
monthly_expense = this_month_df.loc[this_month_df["type"] == "Expense", "amount"].sum()

cat_breakdown = helpers.get_category_breakdown(df)
top_category = cat_breakdown.iloc[0]["category"] if not cat_breakdown.empty else "N/A"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Balance", f"₹{total_balance:,.0f}")
c2.metric("Monthly Income", f"₹{monthly_income:,.0f}")
c3.metric("Monthly Expense", f"₹{monthly_expense:,.0f}")
c4.metric("Top Category (This Month)", top_category)

st.markdown("---")

# --------------------------------------------------------------------------
# Monthly Trend Chart (Income vs Expense, last 12 months)
# --------------------------------------------------------------------------
st.subheader("📈 Monthly Trend — Income vs Expense")
monthly_summary = helpers.get_monthly_summary(df).tail(12)

if monthly_summary.empty:
    st.caption("No data available for trend chart.")
else:
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=monthly_summary["month"], y=monthly_summary["Income"],
        mode="lines+markers", name="Income", line=dict(color="#2ecc71", width=3),
    ))
    fig_trend.add_trace(go.Scatter(
        x=monthly_summary["month"], y=monthly_summary["Expense"],
        mode="lines+markers", name="Expense", line=dict(color="#e74c3c", width=3),
    ))
    fig_trend.update_layout(
        xaxis_title="Month", yaxis_title="Amount (₹)",
        hovermode="x unified", template="plotly_dark", height=400,
    )
    st.plotly_chart(fig_trend, use_container_width=True)

col_pie, col_heat = st.columns(2)

# --------------------------------------------------------------------------
# Category Pie Chart (current month expenses)
# --------------------------------------------------------------------------
with col_pie:
    st.subheader("🥧 This Month's Expense Breakdown")
    if cat_breakdown.empty:
        st.caption("No expenses recorded this month.")
    else:
        fig_pie = px.pie(
            cat_breakdown, names="category", values="amount",
            hole=0.4, template="plotly_dark",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

# --------------------------------------------------------------------------
# Weekday Heatmap
# --------------------------------------------------------------------------
with col_heat:
    st.subheader("🔥 Spending by Weekday")
    heatmap_data = helpers.get_weekday_heatmap_data(df)
    fig_heat = px.imshow(
        [heatmap_data["amount"].values],
        labels=dict(x="Weekday", y="", color="Amount (₹)"),
        x=heatmap_data["weekday"],
        y=[""],
        color_continuous_scale="Reds",
        template="plotly_dark",
        aspect="auto",
    )
    fig_heat.update_layout(height=250)
    st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("---")

# --------------------------------------------------------------------------
# C. Savings Goals progress
# --------------------------------------------------------------------------
st.subheader("🎯 Savings Goals")
goals = db.fetch_all_goals()
if not goals:
    st.caption("No savings goals set yet. Add one in ⚙️ Settings & Goals.")
else:
    for goal in goals:
        pct = 0
        if goal["target_amount"] > 0:
            pct = min((goal["current_saved"] / goal["target_amount"]) * 100, 100)
        st.write(
            f"**{goal['goal_name']}** — ₹{goal['current_saved']:,.0f} / "
            f"₹{goal['target_amount']:,.0f} (Deadline: {goal['deadline']})"
        )
        st.progress(int(pct))

st.markdown("---")

# --------------------------------------------------------------------------
# Text insights
# --------------------------------------------------------------------------
st.subheader("💡 Auto-Generated Insights")
insights = helpers.generate_text_insights(df)
for insight in insights:
    st.write(f"• {insight}")
