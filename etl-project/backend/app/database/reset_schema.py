"""
DANGER: This permanently drops EVERY table in the 'public' schema of your database
and recreates it empty. Only run this intentionally.

Usage (from backend/ with venv active):
    python -m app.database.reset_schema
"""
from sqlalchemy import text
from app.database.connection import engine


def reset_schema():
    confirm = input(
        "This will PERMANENTLY DROP ALL TABLES in the 'public' schema of this database. "
        "Type 'yes' to continue: "
    )
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        return

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))

    print("✅ Schema reset complete. Database is now empty.")


if __name__ == "__main__":
    reset_schema()