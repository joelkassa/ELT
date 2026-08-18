from app.database.db_helpers import get_staging_row, update_staging_status, insert_final_row
from app.services.table_config import FINAL_TABLES


def apply_review_decisions(db, decisions: list):
    """
    decisions: list of dicts, each:
        {
          "staging_id": int,
          "action": "accept" | "reject" | "edit",
          "target_table": str (optional override, required if originally unmapped),
          "edited_data": dict (optional -- fields to overwrite in mapped_data)
        }
    Returns a results list with outcome per staging_id.
    """
    results = []

    for decision in decisions:
        staging_id = decision["staging_id"]
        action = decision["action"]
        row = get_staging_row(db, staging_id)

        if not row:
            results.append({"staging_id": staging_id, "outcome": "error", "detail": "staging row not found"})
            continue

        # Idempotency guard: never let a resubmitted decision downgrade a row that
        # was already finalized (protects against double-submission, network retries, etc.)
        if row["status"] in ("committed", "duplicate_skipped", "rejected"):
            results.append({
                "staging_id": staging_id,
                "outcome": "already_processed",
                "detail": f"row was already finalized as '{row['status']}' in a previous request -- ignored",
            })
            continue

        if action == "reject":
            update_staging_status(db, staging_id, status="rejected")
            db.commit()
            results.append({"staging_id": staging_id, "outcome": "rejected"})
            continue

        # accept or edit
        target_table = decision.get("target_table") or row.get("confirmed_target_table") or row.get("suggested_target_table")
        if not target_table or target_table not in FINAL_TABLES:
            results.append({
                "staging_id": staging_id, "outcome": "error",
                "detail": "no valid target_table specified for this row"
            })
            continue

        raw_data = row["raw_data"]
        mapped_data = dict(raw_data.get("mapped", {}))

        if action == "edit":
            edited = decision.get("edited_data", {})
            mapped_data.update(edited)
            raw_data["mapped"] = mapped_data
            update_staging_status(db, staging_id, status="accepted", confirmed_target_table=target_table, raw_data=raw_data)
        else:
            update_staging_status(db, staging_id, status="accepted", confirmed_target_table=target_table)

        try:
            new_id = insert_final_row(db, target_table, mapped_data, row["source_filename"])
            final_status = "committed" if new_id else "duplicate_skipped"
            update_staging_status(db, staging_id, status=final_status, confirmed_target_table=target_table)
            db.commit()
            if new_id:
                results.append({"staging_id": staging_id, "outcome": "committed", "final_table": target_table, "final_id": new_id})
            else:
                results.append({
                    "staging_id": staging_id, "outcome": "skipped_duplicate",
                    "detail": "row matched an existing unique record; nothing inserted",
                })
        except Exception as e:  # noqa: BLE001
            db.rollback()
            results.append({"staging_id": staging_id, "outcome": "error", "detail": str(e)})
            continue

    return results