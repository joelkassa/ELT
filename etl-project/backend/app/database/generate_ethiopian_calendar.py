"""
Populates the ethiopian_calendar reference table for 2025-2050.
Usage (from backend/ with venv active): python -m app.database.generate_ethiopian_calendar
"""
from sqlalchemy import text
from app.database.connection import engine
from app.services.ethiopian_calendar import generate_calendar_rows

START_YEAR = 2025
END_YEAR = 2050


def run():
    rows = list(generate_calendar_rows(START_YEAR, END_YEAR))
    print(f"Generated {len(rows)} calendar rows ({START_YEAR}-{END_YEAR}). Inserting...")
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM ethiopian_calendar WHERE gregorian_date >= :start AND gregorian_date <= :end"),
            {"start": f"{START_YEAR}-01-01", "end": f"{END_YEAR}-12-31"},
        )
        batch = []
        for row in rows:
            batch.append(row)
            if len(batch) >= 500:
                conn.execute(text("""
                    INSERT INTO ethiopian_calendar
                        (gregorian_date, ethiopian_year, ethiopian_month, ethiopian_month_name,
                         ethiopian_day, ethiopian_fiscal_year, ethiopian_fiscal_quarter)
                    VALUES
                        (:gregorian_date, :ethiopian_year, :ethiopian_month, :ethiopian_month_name,
                         :ethiopian_day, :ethiopian_fiscal_year, :ethiopian_fiscal_quarter)
                """), batch)
                batch = []
        if batch:
            conn.execute(text("""
                INSERT INTO ethiopian_calendar
                    (gregorian_date, ethiopian_year, ethiopian_month, ethiopian_month_name,
                     ethiopian_day, ethiopian_fiscal_year, ethiopian_fiscal_quarter)
                VALUES
                    (:gregorian_date, :ethiopian_year, :ethiopian_month, :ethiopian_month_name,
                     :ethiopian_day, :ethiopian_fiscal_year, :ethiopian_fiscal_quarter)
            """), batch)
    print("✅ Ethiopian calendar reference table populated.")


if __name__ == "__main__":
    run()