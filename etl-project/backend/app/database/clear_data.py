"""
Clears all uploaded data (staging history + the 8 final tables) so you can re-upload
cleanly, WITHOUT touching the grants lookup table or the ethiopian_calendar reference
table (those aren't upload data).

Usage (from backend/ with venv active):
    python -m app.database.clear_data
"""
from sqlalchemy import text
from app.database.connection import engine

DATA_TABLES = [
    "staging_uploads", "ageing", "budget", "income", "expenditure",
    "liquidation", "customer_list", "job_list", "trial_balance",
]


def clear_data():
    confirm = input(
        f"This will permanently DELETE ALL ROWS from: {', '.join(DATA_TABLES)}.\n"
        "grants and ethiopian_calendar will NOT be touched. Type 'yes' to continue: "
    )
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        return

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(DATA_TABLES)} RESTART IDENTITY"))

    print("✅ All uploaded data cleared. Grants and Ethiopian calendar reference tables were left untouched.")


if __name__ == "__main__":
    clear_data()