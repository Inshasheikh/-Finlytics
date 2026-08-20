# 💰 Personal Finance & Experience Tracker

A complete multipage Streamlit app for tracking income, expenses, budgets,
recurring transactions, and savings goals — backed by SQLite, analyzed with
Pandas, and visualized with Plotly.

## Project Structure

```
finance_tracker/
├── app.py                              # Main entry point (sidebar nav, DB init, recurring automation)
├── database.py                         # All SQLite CRUD operations
├── helpers.py                          # Validation, ETL, auto-categorization, insights
├── requirements.txt
├── .streamlit/
│   └── config.toml                     # Dark mode theme
└── pages/
    ├── 1_📥_Add_Transaction.py         # Form + validation + insert
    ├── 2_📊_Dashboard.py               # Metrics, trend chart, pie chart, heatmap, goals
    ├── 3_📈_Reports_&_Insights.py      # Table, edit/delete, CSV export, running balance
    └── 4_⚙️_Settings_&_Goals.py        # Budgets, auto-rules, recurring txns, savings goals
```

## Setup & Run

1. Install dependencies:
   ```bash
   pip install streamlit pandas plotly
   ```
   (or `pip install -r requirements.txt`)

2. From the `finance_tracker/` directory, run:
   ```bash
   streamlit run app.py
   ```

3. Open the URL Streamlit prints (usually `http://localhost:8501`) in your browser.

The SQLite database file (`finance_tracker.db`) is created automatically on
first run in the same folder as `app.py` — no manual setup needed.

## How each feature maps to the code

| Feature | Where |
|---|---|
| Form validation (future date, amount > 0, category required, description ≤ 500 chars) | `helpers.validate_transaction()` |
| Insert with rollback-on-failure | `database.add_transaction()` |
| Cached data load (`@st.cache_data(ttl=60)`) | `app.py`, and each page's own `load_all_transactions()` |
| Monthly summary / category breakdown / running balance / budget comparison | `helpers.get_monthly_summary`, `get_category_breakdown`, `calculate_running_balance`, `compare_with_budget` |
| Trend line chart, pie chart, weekday heatmap | `pages/2_📊_Dashboard.py` (Plotly) |
| Auto-generated text insights | `helpers.generate_text_insights()` |
| Budget alerts (sidebar/dashboard) | `helpers.get_all_budget_alerts()`, shown in `app.py` and Dashboard |
| Edit / Delete / CSV export | `pages/3_📈_Reports_&_Insights.py` |
| Auto-categorization by keyword | `helpers.auto_categorize()`, rules managed in Settings |
| Recurring transactions automation | `helpers.process_recurring()`, called once per session in `app.py` |
| Savings goals + progress bars | `database.py` savings_goals functions, Dashboard + Settings pages |
| Dark mode | `.streamlit/config.toml` |

## Notes

- All DB operations are wrapped in `try/except` with rollback on failure; errors are printed to the console and surfaced to the user via `st.error`.
- Empty-data states are handled gracefully throughout (e.g. "No data available" instead of broken charts).
- `process_recurring()` runs once per Streamlit session (tracked via `st.session_state`) so it doesn't re-fire on every rerun/widget interaction.
- Currency is displayed in ₹ (INR) per the original spec — change the symbol in `helpers.py` / page files if you need a different currency.
