import json
from sqlalchemy import text
from app.services.table_config import FINAL_TABLES


def normalize_value_for_comparison(value):
    """
    Normalize a value for duplicate comparison, ignoring formatting variations.
    - None and empty strings are treated as equivalent
    - Strings are lowercased and stripped
    - Numbers are converted to float for comparison
    - Returns a normalized, hashable value
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    
    if isinstance(value, str):
        normalized = value.strip().lower()
        # Try to parse as float for numeric comparison
        try:
            return float(normalized)
        except (ValueError, TypeError):
            return normalized
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # For other types, convert to string and normalize
    try:
        normalized = str(value).strip().lower()
        # Try to parse as float
        try:
            return float(normalized)
        except (ValueError, TypeError):
            return normalized
    except Exception:
        return None


def full_rows_match(row1: dict, row2: dict, table_columns: list):
    """
    Compare two rows (dictionaries) for complete match, ignoring formatting variations.
    Returns True only if all columns have equivalent values (using normalized comparison).
    """
    for col in table_columns:
        val1 = normalize_value_for_comparison(row1.get(col))
        val2 = normalize_value_for_comparison(row2.get(col))
        if val1 != val2:
            return False
    return True


def get_all_grants(db):
    rows = db.execute(text("SELECT id, name FROM grants ORDER BY name")).mappings().all()
    return [dict(r) for r in rows]


def get_or_create_grant_id(db, grant_name: str) -> int:
    existing = db.execute(text("SELECT id FROM grants WHERE name = :name"), {"name": grant_name}).first()
    if existing:
        return existing[0]
    result = db.execute(text("INSERT INTO grants (name) VALUES (:name) RETURNING id"), {"name": grant_name})
    new_id = result.scalar_one()
    db.commit()
    return new_id


def insert_staging_row(db, session_id, source_filename, sheet_name, row_index, grant_name, year,
                        raw_data: dict, suggested_target_table, status, validation_issues: dict):
    result = db.execute(
        text("""
            INSERT INTO staging_uploads
                (session_id, source_filename, sheet_name, row_index, grant_name, year, raw_data,
                 suggested_target_table, confirmed_target_table, status, validation_issues)
            VALUES
                (:session_id, :source_filename, :sheet_name, :row_index, :grant_name, :year,
                 CAST(:raw_data AS JSONB), :suggested_target_table, :suggested_target_table,
                 :status, CAST(:validation_issues AS JSONB))
            RETURNING id
        """),
        {
            "session_id": session_id, "source_filename": source_filename, "sheet_name": sheet_name,
            "row_index": row_index, "grant_name": grant_name, "year": year,
            "raw_data": json.dumps(raw_data, default=str),
            "suggested_target_table": suggested_target_table, "status": status,
            "validation_issues": json.dumps(validation_issues, default=str),
        },
    )
    return result.scalar_one()


def get_staging_row(db, staging_id: int):
    row = db.execute(text("SELECT * FROM staging_uploads WHERE id = :id"), {"id": staging_id}).mappings().first()
    return dict(row) if row else None


def get_pending_staging_rows(db, session_id: str = None):
    if session_id:
        rows = db.execute(
            text("SELECT * FROM staging_uploads WHERE status = 'pending' AND session_id = :sid ORDER BY uploaded_at DESC"),
            {"sid": session_id},
        ).mappings().all()
    else:
        rows = db.execute(text("SELECT * FROM staging_uploads WHERE status = 'pending' ORDER BY uploaded_at DESC")).mappings().all()
    return [dict(r) for r in rows]


def count_pending_in_session(db, session_id: str) -> int:
    return db.execute(
        text("SELECT COUNT(*) FROM staging_uploads WHERE session_id = :sid AND status = 'pending'"),
        {"sid": session_id},
    ).scalar_one()


def update_staging_status(db, staging_id: int, status: str, confirmed_target_table: str = None, raw_data: dict = None):
    params = {"id": staging_id, "status": status}
    set_clauses = ["status = :status"]
    if confirmed_target_table is not None:
        set_clauses.append("confirmed_target_table = :confirmed_target_table")
        params["confirmed_target_table"] = confirmed_target_table
    if raw_data is not None:
        set_clauses.append("raw_data = CAST(:raw_data AS JSONB)")
        params["raw_data"] = json.dumps(raw_data, default=str)
    db.execute(text(f"UPDATE staging_uploads SET {', '.join(set_clauses)} WHERE id = :id"), params)


def row_exists_in_final_table(db, target_table: str, unique_key_values: dict) -> bool:
    if target_table not in FINAL_TABLES or not unique_key_values:
        return False
    if any(v is None for v in unique_key_values.values()):
        return False
    where_clause = " AND ".join(f"{k}::text = :{k}" for k in unique_key_values)
    params = {k: str(v) for k, v in unique_key_values.items()}
    query = text(f"SELECT 1 FROM {target_table} WHERE {where_clause} LIMIT 1")
    result = db.execute(query, params).first()
    return result is not None


def full_row_exists_in_final_table(db, target_table: str, mapped_data: dict) -> bool:
    """
    Check if a complete row already exists in the final table.
    Compares ALL columns (not just unique key) using normalized value comparison.
    """
    if target_table not in FINAL_TABLES:
        return False
    
    cfg = FINAL_TABLES[target_table]
    table_columns = cfg["columns"]
    
    # Query all rows from the target table
    query = text(f"SELECT {', '.join(table_columns)} FROM {target_table}")
    existing_rows = db.execute(query).mappings().all()
    
    # Compare current row against each existing row
    for existing_row in existing_rows:
        existing_dict = dict(existing_row)
        if full_rows_match(mapped_data, existing_dict, table_columns):
            return True
    
    return False


def insert_final_row(db, target_table: str, mapped_data: dict, source_filename: str):
    cfg = FINAL_TABLES[target_table]
    columns = cfg["columns"]
    insert_data = {col: mapped_data.get(col) for col in columns}
    insert_data["source_filename"] = source_filename
    col_names = list(insert_data.keys())
    placeholders = ", ".join(f":{c}" for c in col_names)
    col_list = ", ".join(col_names)
    query = text(f"""
        INSERT INTO {target_table} ({col_list})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
        RETURNING id
    """)
    result = db.execute(query, insert_data)
    row = result.first()
    return row[0] if row else None


def get_existing_labels_for_id(db, table_name: str, id_field: str, label_field: str, id_value):
    """
    Return the set of distinct (raw) label values already stored in the final table
    for this id -- used to catch cases where the same id was previously saved with
    a different spelling of its label (e.g. customer_id 123 = "Tigray" vs "Tgray").
    """
    if id_value is None or table_name not in FINAL_TABLES:
        return set()
    query = text(f"SELECT DISTINCT {label_field} FROM {table_name} WHERE {id_field}::text = :id_value")
    rows = db.execute(query, {"id_value": str(id_value)}).all()
    return {r[0] for r in rows if r[0] is not None}


def add_validation_issue(db, staging_id: int, issue_key: str, message: str):
    """
    Append a validation issue to a staging row that was already inserted earlier
    in the same batch (used to back-flag the first-seen row when a later row in
    the batch reveals an id/label conflict with it).
    """
    row = db.execute(
        text("SELECT validation_issues FROM staging_uploads WHERE id = :id"), {"id": staging_id}
    ).first()
    if not row:
        return
    issues = dict(row[0] or {})
    if issue_key not in issues:
        issues[issue_key] = message
        db.execute(
            text("UPDATE staging_uploads SET validation_issues = CAST(:vi AS JSONB) WHERE id = :id"),
            {"vi": json.dumps(issues, default=str), "id": staging_id},
        )