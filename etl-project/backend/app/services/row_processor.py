from app.services.table_config import FINAL_TABLES
from app.utils.validators import normalize_date, is_missing
from app.services.customer_classifier import classify_customer_name

TOTAL_ROW_KEYWORDS = ["total", "subtotal", "sub-total", "sub total", "grand total", "totals"]


def looks_like_total_row(raw_row: dict) -> bool:
    for value in raw_row.values():
        if isinstance(value, str):
            v = value.strip().lower()
            if v in TOTAL_ROW_KEYWORDS:
                return True
    return False


def build_mapped_row(raw_row: dict, column_mapping: dict, target_table: str,
                      grant_id: int, year: int = None):
    """
    grant_id: resolved once per file (from the folder name), passed in directly.
    year: resolved once per file (from folder name) for "manual" tables, or None for
          "date"-sourced tables (extracted per-row below instead).
    """
    if target_table not in FINAL_TABLES:
        return {}, {"target_table": f"unknown target table '{target_table}'"}

    cfg = FINAL_TABLES[target_table]
    mapped = {}
    issues = {}

    if looks_like_total_row(raw_row):
        issues["total_row"] = "this looks like a Total/Subtotal row -- review carefully, likely should be rejected to avoid double-counting"

    for source_header, value in raw_row.items():
        field, conf = column_mapping.get(source_header, (None, 0.0))
        if field and field in cfg["columns"]:
            mapped[field] = value

    mapped["grant_id"] = grant_id

    for date_field in cfg["date_fields"]:
        if date_field in mapped and not is_missing(mapped[date_field]):
            iso_date, display, note = normalize_date(mapped[date_field])
            mapped[date_field] = iso_date
            mapped[f"{date_field}_display"] = display
            if iso_date is None:
                issues[date_field] = note or f"could not parse '{date_field}' value"

    year_source = cfg["year_source"]
    if year_source == "manual":
        if is_missing(year):
            issues["year"] = "year could not be determined from the folder structure"
        else:
            mapped["year"] = int(year)
    else:
        _, source_date_field = year_source
        iso_date = mapped.get(source_date_field)
        if iso_date:
            try:
                mapped["year"] = int(iso_date[:4])
            except (ValueError, TypeError):
                issues["year"] = f"could not extract year from '{source_date_field}'"
        else:
            issues["year"] = f"could not extract year -- '{source_date_field}' is missing/unparseable"

    for num_field in cfg.get("numeric_fields", []):
        if num_field not in mapped or is_missing(mapped.get(num_field)):
            mapped[num_field] = 0
        else:
            try:
                mapped[num_field] = float(mapped[num_field])
            except (ValueError, TypeError):
                issues[num_field] = f"'{num_field}' value '{mapped[num_field]}' is not a valid number"
                mapped[num_field] = 0

    # Auto-classify category for customer_list rows (category is system-managed,
    # not supplied in the source Excel -- see table_config.system_managed_fields).
    # Uses the standardization logic ported from the Customer_List_Standard_Mapping
    # prototype (see customer_classifier.py).
    if target_table == "customer_list" and "customer_name" in mapped:
        category, standardized_name = classify_customer_name(mapped["customer_name"])
        mapped["category"] = category
        if category is None:
            issues["category"] = f"could not auto-classify category for '{mapped['customer_name']}' -- please set manually"

    numeric_set = set(cfg.get("numeric_fields", []))
    system_managed = set(cfg.get("system_managed_fields", []))
    for col in cfg["columns"]:
        if col in ("grant_id", "year") or col in numeric_set or col in system_managed:
            continue
        if col not in mapped or is_missing(mapped.get(col)):
            issues.setdefault(col, f"'{col}' not found or empty in source row -- please verify/edit")

    return mapped, issues


def build_unique_key_values(mapped: dict, target_table: str):
    cfg = FINAL_TABLES[target_table]
    return {k: mapped.get(k) for k in cfg["unique_key"]}