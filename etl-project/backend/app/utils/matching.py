import re
import difflib


def normalize_header(header: str) -> str:
    """Lowercase, strip, and collapse all punctuation/whitespace down to single spaces
    for comparison (handles headers like 'Amount($)', 'Invoice/CM #', '6m-1Yer', etc.)."""
    if header is None:
        return ""
    h = str(header).strip().lower()
    h = re.sub(r"[^a-z0-9\s]", " ", h)
    h = re.sub(r"\s+", " ", h)
    return h.strip()


def best_field_for_header(header: str, synonyms: dict, threshold: float = 0.55):
    """
    Given a raw Excel header and a {field_name: [synonym, ...]} dict,
    return (field_name, confidence) for the best match, or (None, 0) if nothing clears the threshold.

    Matching is token-based (not raw character similarity) to avoid false positives from
    shared prefixes/substrings, e.g. "Account Type" should NOT match "account_code" just
    because both start with "account".
    """
    norm_header = normalize_header(header)
    if not norm_header:
        return None, 0.0

    header_tokens = norm_header.split()
    header_token_set = set(header_tokens)

    best_field = None
    best_score = 0.0

    for field, syns in synonyms.items():
        candidates = [normalize_header(field)] + [normalize_header(s) for s in syns]
        for cand in candidates:
            if norm_header == cand:
                return field, 1.0

            cand_tokens = cand.split()
            cand_token_set = set(cand_tokens)
            score = 0.0

            if len(cand_tokens) > 1 and cand_token_set.issubset(header_token_set):
                # Multi-word synonym fully present as whole words in the header
                score = 0.9
            elif len(cand_tokens) == 1 and cand in header_token_set:
                # Single-word synonym present as a whole word in the header
                score = 0.9
            else:
                # Fuzzy fallback for typos/abbreviations -- compare token-to-token,
                # only for tokens long enough that similarity is meaningful (avoids
                # short-word collisions like "fy" incidentally resembling "fye").
                for ht in header_tokens:
                    for ct in cand_tokens:
                        if len(ht) >= 4 and len(ct) >= 4:
                            ratio = difflib.SequenceMatcher(None, ht, ct).ratio()
                            score = max(score, ratio * 0.85)

            if score > best_score:
                best_score = score
                best_field = field

    if best_score >= threshold:
        return best_field, round(best_score, 2)
    return None, 0.0


def guess_table_from_text(text_value: str, table_keywords: dict):
    """
    text_value: e.g. filename + sheet name combined, lowercased.
    table_keywords: {table_name: [keyword, ...]}
    Returns (table_name, confidence) best guess, or (None, 0).
    """
    norm = normalize_header(text_value)
    best_table, best_score = None, 0.0
    for table, keywords in table_keywords.items():
        for kw in keywords:
            kw_norm = normalize_header(kw)
            if kw_norm in norm:
                score = 0.95
            else:
                score = difflib.SequenceMatcher(None, norm, kw_norm).ratio()
            if score > best_score:
                best_score = score
                best_table = table
    if best_score >= 0.5:
        return best_table, round(best_score, 2)
    return None, 0.0