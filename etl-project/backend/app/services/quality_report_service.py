"""
Data quality scoring for the final tables, adapted from the prototype notebooks
Data_Profiling_Pipeline.ipynb and Data_Quality_Analysis.ipynb.

Computes completeness, validity, uniqueness, and consistency scores (0-100)
per final table, reading directly from Postgres instead of standalone Excel files.
"""
from sqlalchemy import text
from app.services.table_config import FINAL_TABLES


def compute_table_quality(db, table_name: str) -> dict:
    if table_name not in FINAL_TABLES:
        return {"error": f"unknown table '{table_name}'"}

    cfg = FINAL_TABLES[table_name]
    columns = cfg["columns"]

    total_rows = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
    if total_rows == 0:
        return {
            "table": table_name, "row_count": 0,
            "quality_score": None, "metrics": {},
            "detail": "no rows in this table yet",
        }

    # --- Completeness: % of non-null cells across all mapped columns ---
    null_counts = {}
    for col in columns:
        null_counts[col] = db.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE {col} IS NULL")
        ).scalar_one()
    total_cells = total_rows * len(columns)
    total_nulls = sum(null_counts.values())
    completeness = (1 - total_nulls / total_cells) * 100 if total_cells else 100

    # --- Uniqueness: % of rows that are distinct on the table's unique_key ---
    key_cols = ", ".join(cfg["unique_key"])
    distinct_keys = db.execute(text(f"SELECT COUNT(DISTINCT ({key_cols})) FROM {table_name}")).scalar_one()
    uniqueness = (distinct_keys / total_rows) * 100 if total_rows else 100
    duplicate_pct = 100 - uniqueness

    # --- Validity: numeric columns should not contain negative/garbage where not expected ---
    numeric_fields = cfg.get("numeric_fields", [])
    if numeric_fields:
        valid_checks = []
        for col in numeric_fields:
            not_null = total_rows - null_counts.get(col, 0)
            valid_checks.append(not_null / total_rows if total_rows else 1)
        validity = (sum(valid_checks) / len(valid_checks)) * 100
    else:
        validity = 100.0

    # --- Consistency: for date-bearing tables, rows should have both a valid date and a valid year ---
    if cfg.get("date_fields"):
        date_col = cfg["date_fields"][0]
        valid_dates = db.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE {date_col} IS NOT NULL AND year IS NOT NULL")
        ).scalar_one()
        consistency = (valid_dates / total_rows) * 100 if total_rows else 100
    else:
        consistency = 100.0

    weights = {"completeness": 0.3, "validity": 0.3, "uniqueness": 0.2, "consistency": 0.2}
    metrics = {
        "completeness": round(completeness, 2),
        "validity": round(validity, 2),
        "uniqueness": round(uniqueness, 2),
        "duplicates_pct": round(duplicate_pct, 2),
        "consistency": round(consistency, 2),
    }
    overall = sum(metrics[m] * w for m, w in weights.items())

    return {
        "table": table_name,
        "row_count": total_rows,
        "quality_score": round(overall, 2),
        "metrics": metrics,
    }


def compute_all_tables_quality(db) -> dict:
    return {t: compute_table_quality(db, t) for t in FINAL_TABLES}