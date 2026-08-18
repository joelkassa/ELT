import pandas as pd
from io import BytesIO

from app.services.table_config import FINAL_TABLES, FIELD_SYNONYMS
from app.utils.matching import best_field_for_header, guess_table_from_text


def read_excel_sheets(file_bytes: bytes, filename: str):
    """
    Returns a list of dicts, one per sheet:
        {"sheet_name": str, "headers": [str], "rows": [dict]}
    """
    xls = pd.ExcelFile(BytesIO(file_bytes))
    sheets = []
    for sheet_name in xls.sheet_names:
        df = xls.parse(sheet_name, dtype=object)
        df = df.dropna(how="all")  # drop fully empty rows
        df = df.where(pd.notnull(df), None)  # convert NaN/NaT -> None (valid JSON, detected as "missing")
        headers = [str(c) for c in df.columns]
        rows = df.to_dict(orient="records")
        if rows:
            sheets.append({"sheet_name": sheet_name, "headers": headers, "rows": rows})
    return sheets


def suggest_target_table(filename: str, sheet_name: str, headers: list):
    """
    Combines filename + sheet name keyword match with header-overlap scoring
    to guess which of the 8 final tables this sheet belongs to.
    """
    keyword_map = {t: cfg["keywords"] for t, cfg in FINAL_TABLES.items()}
    text_guess, text_conf = guess_table_from_text(f"{filename} {sheet_name}", keyword_map)

    header_scores = {}
    for table, cfg in FINAL_TABLES.items():
        table_fields = set(cfg["columns"])
        matched = 0
        for h in headers:
            field, conf = best_field_for_header(h, FIELD_SYNONYMS)
            if field and field in table_fields:
                matched += 1
        header_scores[table] = matched / max(len(table_fields), 1)

    best_header_table = max(header_scores, key=header_scores.get)
    best_header_score = header_scores[best_header_table]

    if text_guess and text_conf >= 0.75:
        return text_guess, text_conf
    if best_header_score >= 0.4:
        return best_header_table, round(best_header_score, 2)
    if text_guess:
        return text_guess, text_conf

    return None, 0.0


def suggest_column_mapping(headers: list):
    """
    Returns {source_header: (field_name_or_None, confidence)}
    """
    mapping = {}
    for h in headers:
        field, conf = best_field_for_header(h, FIELD_SYNONYMS)
        mapping[h] = (field, conf)
    return mapping