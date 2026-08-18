"""
Run this once to create the staging table + 8 final tables inside your
existing PostgreSQL database (does NOT create a new database).

Usage (from the backend/ folder, with venv active):
    python -m app.database.create_tables
"""
from pathlib import Path
from sqlalchemy import text
from app.database.connection import engine


def run_migration():
    schema_path = Path(__file__).parent / "schema.sql"
    sql_script = schema_path.read_text()

    with engine.begin() as conn:
        for statement in sql_script.split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))

    print("✅ staging_uploads + all 8 final tables created/verified successfully.")


if __name__ == "__main__":
    run_migration()
