import uuid

from app.services.excel_parser import read_excel_sheets, suggest_target_table, suggest_column_mapping
from app.services.row_processor import build_mapped_row, build_unique_key_values
from app.services.table_config import ALL_TABLE_NAMES, FINAL_TABLES
from app.utils.validators import is_missing
from app.database.db_helpers import (
    insert_staging_row, row_exists_in_final_table, full_row_exists_in_final_table,
    get_or_create_grant_id, full_rows_match, normalize_value_for_comparison,
    get_existing_labels_for_id, add_validation_issue,
)


def ingest_files(db, files_with_meta: list):
    """
    files_with_meta: list of (filename, file_bytes, grant_name, year_or_None)
    Returns (session_id, preview grouped by suggested target table)
    """
    session_id = uuid.uuid4().hex
    preview = {t: [] for t in ALL_TABLE_NAMES}
    preview["_unmapped"] = []

    # Track full rows in batch for duplicate detection
    seen_rows_in_batch = []  # List of (target_table, mapped_data_dict)

    # Track (table, id_field, normalized_id) -> list of {norm, orig, staging_id, issues_ref}
    # for the id/label consistency check (e.g. same customer_id, different spelling of name)
    seen_labels_by_id = {}

    grant_id_cache = {}

    for filename, file_bytes, grant_name, year in files_with_meta:
        if grant_name not in grant_id_cache:
            grant_id_cache[grant_name] = get_or_create_grant_id(db, grant_name)
        grant_id = grant_id_cache[grant_name]

        sheets = read_excel_sheets(file_bytes, filename)

        for sheet in sheets:
            sheet_name = sheet["sheet_name"]
            headers = sheet["headers"]
            rows = sheet["rows"]

            target_table, table_confidence = suggest_target_table(filename, sheet_name, headers)
            column_mapping = suggest_column_mapping(headers)

            for idx, raw_row in enumerate(rows):
                if target_table is None:
                    staging_id = insert_staging_row(
                        db, session_id, filename, sheet_name, idx, grant_name, year,
                        raw_data={"original": raw_row, "mapped": {}},
                        suggested_target_table=None, status="pending",
                        validation_issues={"target_table": "could not auto-detect target table -- please select manually"},
                    )
                    preview["_unmapped"].append({
                        "staging_id": staging_id, "source_filename": filename, "sheet_name": sheet_name,
                        "grant_name": grant_name, "year": year, "original_row": raw_row, "mapped_data": {},
                        "issues": {"target_table": "could not auto-detect -- please select manually"},
                        "suggested_target_table": None, "mapping_confidence": 0.0,
                    })
                    continue

                mapped_data, issues = build_mapped_row(raw_row, column_mapping, target_table, grant_id, year)

                cfg = FINAL_TABLES[target_table]
                table_columns = cfg["columns"]

                # Check for in-batch duplicates: compare full rows against all previously seen rows
                for seen_table, seen_data in seen_rows_in_batch:
                    if seen_table == target_table and full_rows_match(mapped_data, seen_data, table_columns):
                        issues["duplicate"] = "duplicate row within this upload batch"
                        break

                # If no in-batch duplicate found, check if it exists in the database
                if "duplicate" not in issues:
                    if full_row_exists_in_final_table(db, target_table, mapped_data):
                        issues["duplicate"] = "a matching record already exists in the database"

                # Track this row for future comparisons in the batch
                seen_rows_in_batch.append((target_table, mapped_data))

                # -- id/label consistency check: same id, different label spelling --
                # This fires independently of the duplicate check above -- it does not
                # care whether the rest of the row matches, only whether the id has been
                # seen before (in this batch or in the DB) attached to a different label.
                for id_field, label_field in cfg.get("id_label_pairs", []):
                    id_val = mapped_data.get(id_field)
                    label_val = mapped_data.get(label_field)
                    if is_missing(id_val) or is_missing(label_val):
                        continue

                    norm_id = normalize_value_for_comparison(id_val)
                    norm_label = normalize_value_for_comparison(label_val)
                    issue_key = f"label_conflict__{label_field}"
                    key = (target_table, id_field, norm_id)
                    prior_entries = seen_labels_by_id.setdefault(key, [])

                    conflict_hit = None
                    for entry in prior_entries:
                        if entry["norm"] != norm_label:
                            conflict_hit = entry
                            break

                    if conflict_hit is not None:
                        issues[issue_key] = (
                            f"'{id_field}' = {id_val!r} appears with a different '{label_field}' "
                            f"earlier in this upload: {conflict_hit['orig']!r} vs {label_val!r} -- "
                            f"please verify which spelling is correct"
                        )
                        # back-flag the earlier row too (in memory for this response, and in the DB)
                        if issue_key not in conflict_hit["issues_ref"]:
                            back_message = (
                                f"'{id_field}' = {id_val!r} appears with a different '{label_field}' "
                                f"later in this upload: {conflict_hit['orig']!r} vs {label_val!r} -- "
                                f"please verify which spelling is correct"
                            )
                            conflict_hit["issues_ref"][issue_key] = back_message
                            add_validation_issue(db, conflict_hit["staging_id"], issue_key, back_message)
                    else:
                        existing_labels = get_existing_labels_for_id(db, target_table, id_field, label_field, id_val)
                        db_conflicts = [l for l in existing_labels if normalize_value_for_comparison(l) != norm_label]
                        if db_conflicts:
                            issues[issue_key] = (
                                f"'{id_field}' = {id_val!r} already exists in the database with a different "
                                f"'{label_field}': {db_conflicts[0]!r} vs {label_val!r} -- "
                                f"please verify which spelling is correct"
                            )

                staging_id = insert_staging_row(
                    db, session_id, filename, sheet_name, idx, grant_name, year,
                    raw_data={"original": raw_row, "mapped": mapped_data},
                    suggested_target_table=target_table, status="pending", validation_issues=issues,
                )

                preview_entry = {
                    "staging_id": staging_id, "source_filename": filename, "sheet_name": sheet_name,
                    "grant_name": grant_name, "year": year, "original_row": raw_row,
                    "mapped_data": mapped_data, "issues": issues,
                    "suggested_target_table": target_table, "mapping_confidence": table_confidence,
                }
                preview[target_table].append(preview_entry)

                # register this row's (id, label) for future conflict checks in this batch
                for id_field, label_field in cfg.get("id_label_pairs", []):
                    id_val = mapped_data.get(id_field)
                    label_val = mapped_data.get(label_field)
                    if is_missing(id_val) or is_missing(label_val):
                        continue
                    key = (target_table, id_field, normalize_value_for_comparison(id_val))
                    seen_labels_by_id.setdefault(key, []).append({
                        "norm": normalize_value_for_comparison(label_val),
                        "orig": label_val,
                        "staging_id": staging_id,
                        "issues_ref": issues,
                    })

    db.commit()
    return session_id, {k: v for k, v in preview.items() if v}