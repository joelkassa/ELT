import difflib
from datetime import datetime, date
from dateutil import parser as dateutil_parser

try:
    import pycountry
except ImportError:  # pragma: no cover
    pycountry = None

_ALL_COUNTRY_NAMES = None


def _get_all_country_names():
    global _ALL_COUNTRY_NAMES
    if _ALL_COUNTRY_NAMES is None and pycountry is not None:
        _ALL_COUNTRY_NAMES = [c.name for c in pycountry.countries]
    return _ALL_COUNTRY_NAMES or []


# Common aliases/misspellings that pycountry's fuzzy search won't catch cleanly
COUNTRY_ALIASES = {
    "usa": "United States",
    "us": "United States",
    "u.s.a": "United States",
    "uk": "United Kingdom",
    "england": "United Kingdom",
    "uae": "United Arab Emirates",
    "ethiopa": "Ethiopia",
    "ethopia": "Ethiopia",
    "drc": "Congo, The Democratic Republic of the",
    "congo drc": "Congo, The Democratic Republic of the",
    "south korea": "Korea, Republic of",
    "north korea": "Korea, Democratic People's Republic of",
    "ivory coast": "Cote d'Ivoire",
    "tanzania": "Tanzania, United Republic of",
    "russia": "Russian Federation",
}


def normalize_date(value):
    """
    Try to parse any reasonable date format and return:
        (iso_date_for_db, display_ddmmyyyy, issue_note or None)
    Never rejects a value outright -- if parsing truly fails, returns (None, original_str, "unparseable date").
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, None, None

    if isinstance(value, (datetime, date)):
        d = value if isinstance(value, date) and not isinstance(value, datetime) else value.date()
        return d.isoformat(), d.strftime("%d/%m/%Y"), None

    raw = str(value).strip()

    # Try day-first first (our target format is dd/mm/yyyy)
    for dayfirst in (True, False):
        try:
            parsed = dateutil_parser.parse(raw, dayfirst=dayfirst, fuzzy=False)
            display = parsed.strftime("%d/%m/%Y")
            note = None
            # Flag if the original text didn't already look like dd/mm/yyyy
            if not _looks_like_ddmmyyyy(raw):
                note = f"reformatted '{raw}' -> '{display}'"
            return parsed.date().isoformat(), display, note
        except (ValueError, OverflowError):
            continue

    return None, raw, f"unrecognized date format: '{raw}'"


def _looks_like_ddmmyyyy(raw: str) -> bool:
    import re
    return bool(re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", raw.strip()))


def normalize_country(value):
    """
    Returns (standardized_name, issue_note or None).
    Never rejects -- worst case returns the original text with a warning note.
    """
    if value is None or not str(value).strip():
        return None, None

    raw = str(value).strip()
    key = raw.lower().strip(".")

    if key in COUNTRY_ALIASES:
        standardized = COUNTRY_ALIASES[key]
        note = None if standardized.lower() == raw.lower() else f"standardized '{raw}' -> '{standardized}'"
        return standardized, note

    if pycountry is not None:
        try:
            match = pycountry.countries.lookup(raw)
            standardized = match.name
            note = None if standardized.lower() == raw.lower() else f"standardized '{raw}' -> '{standardized}'"
            return standardized, note
        except LookupError:
            candidates = _get_all_country_names()
            close = difflib.get_close_matches(raw, candidates, n=1, cutoff=0.72)
            if close:
                return close[0], f"standardized '{raw}' -> '{close[0]}' (fuzzy match, please verify)"

    return raw, f"unrecognized country '{raw}' -- please verify manually"


def is_missing(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())
