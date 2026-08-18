"""
Post-review summary: compares what was in the source Excel files against what
actually landed in the database, per upload session.
"""
from collections import defaultdict
from sqlalchemy import text

# Which field represents "the total" worth comparing, per table.
# Only income is wired up for now -- add more here later (e.g. "expenditure": "debit").
COMPARISON_FIELD_BY_TABLE = {
    "income": "credit",
}


def _get_mapped(row, field):
    mapped = (row.get("raw_data") or {}).get("mapped") or {}
    val = mapped.get(field)
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def compute_summary(db, session_id: str, mode: str = "per_grant"):
    rows = db.execute(text("SELECT * FROM staging_uploads WHERE session_id = :sid"), {"sid": session_id}).mappings().all()
    rows = [dict(r) for r in rows]

    groups = defaultdict(list)
    for r in rows:
        table = r.get("confirmed_target_table") or r.get("suggested_target_table")
        if not table:
            continue
        effective_year = r["year"]
        if effective_year is None:
            effective_year = (r.get("raw_data") or {}).get("mapped", {}).get("year")
        groups[(r["grant_name"], effective_year, table)].append(r)

    per_grant_results = []
    for (grant_name, year, table), grp_rows in groups.items():
        excel_rows = [r for r in grp_rows if not (r.get("validation_issues") or {}).get("total_row")]
        committed_rows = [r for r in grp_rows if r["status"] == "committed"]

        entry = {
            "grant_name": grant_name, "year": year, "table": table,
            "excel_row_count": len(excel_rows), "db_row_count": len(committed_rows),
            "rejected_count": len([r for r in grp_rows if r["status"] == "rejected"]),
            "duplicate_skipped_count": len([r for r in grp_rows if r["status"] == "duplicate_skipped"]),
            "still_pending_count": len([r for r in grp_rows if r["status"] == "pending"]),
        }

        comparison_field = COMPARISON_FIELD_BY_TABLE.get(table)
        if comparison_field:
            excel_total = sum(_get_mapped(r, comparison_field) for r in excel_rows)
            db_total = sum(_get_mapped(r, comparison_field) for r in committed_rows)
            entry[f"{table}_{comparison_field}_excel_total"] = round(excel_total, 2)
            entry[f"{table}_{comparison_field}_db_total"] = round(db_total, 2)
            entry[f"{table}_{comparison_field}_difference"] = round(excel_total - db_total, 2)

        per_grant_results.append(entry)

    per_grant_results.sort(key=lambda e: (str(e["grant_name"]), str(e["year"]), e["table"]))

    if mode == "combined":
        combined = defaultdict(lambda: defaultdict(float))
        counts = defaultdict(lambda: defaultdict(int))
        for e in per_grant_results:
            key = (e["year"], e["table"])
            for count_field in ["excel_row_count", "db_row_count", "rejected_count", "duplicate_skipped_count", "still_pending_count"]:
                counts[key][count_field] += e[count_field]
            for k, v in e.items():
                if k.endswith("_excel_total") or k.endswith("_db_total"):
                    combined[key][k] += v

        results = []
        for (year, table), count_vals in counts.items():
            entry = {"year": year, "table": table, **count_vals}
            for k, v in combined[(year, table)].items():
                entry[k] = round(v, 2)
            for k in list(entry.keys()):
                if k.endswith("_excel_total"):
                    base = k[: -len("_excel_total")]
                    db_key = f"{base}_db_total"
                    if db_key in entry:
                        entry[f"{base}_difference"] = round(entry[k] - entry[db_key], 2)
            results.append(entry)
        results.sort(key=lambda e: (str(e["year"]), e["table"]))
        return results

    return per_grant_results