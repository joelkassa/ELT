"""
Customer name standardization & category classification.

Adapted from the StandardGenerator prototype (Customer_List_Standard_Mapping.ipynb).
Since customer_list Excel files now only contain customer_id + customer_name (no
category column), this module auto-fills `category` by matching the cleaned
customer_name against known region / agency / donor / university / hospital aliases.

Usage:
    category, standardized_name = classify_customer_name(raw_name)
"""
import re

# --- Alias maps (trimmed from the notebook -- extend these lists as needed) ---

REGION_ALIASES = {
    "addis ababa": "addis ababa", "addis ababa city": "addis ababa",
    "addis ababa city admin": "addis ababa", "addis ababa city admin.": "addis ababa",
    "afar": "afar", "afar region": "afar", "afar regional state": "afar",
    "amhara": "amhara", "amhara region": "amhara", "amhara regional state": "amhara",
    "benishangul": "benishangul-gumuz", "benishangul gumuz": "benishangul-gumuz",
    "beneshangul": "benishangul-gumuz",
    "dire dawa": "dire dawa", "dire dawa city admin": "dire dawa",
    "gambela": "gambela", "gambella": "gambela", "gambela region": "gambela",
    "harari": "harari", "harar": "harari", "hareri": "harari",
    "oromia": "oromia", "oromia region": "oromia", "oromia regional state": "oromia",
    "sidama": "sidama", "sidam": "sidama", "sidama region": "sidama",
    "somali": "somali", "somale": "somali", "somalia": "somali",
    "south ethiopia": "southwest ethiopia", "southwest ethiopia": "southwest ethiopia",
    "south west ethiopia": "southwest ethiopia",
    "tigray": "tigray", "tigray region": "tigray", "tigray regional state": "tigray",
    "central ethiopia": "central ethiopia", "central ethiopia region": "central ethiopia",
}

REGION_CODES = {
    "tigray": "XR001", "afar": "XR002", "amhara": "XR003", "oromia": "XR004",
    "somali": "XR005", "benishangul-gumuz": "XR006", "south ethiopia": "XR007",
    "gambela": "XR008", "harari": "XR009", "dire dawa": "XR010",
    "addis ababa": "XR011", "sidama": "XR012", "southwest ethiopia": "XR013",
    "central ethiopia": "XR014",
}

DONOR_ALIASES = {
    "unicef": "UNICEF", "unicef int. fun.": "UNICEF", "unicef hpf": "UNICEF",
    "who": "WHO", "who inter fund": "WHO",
    "unfpa": "UNFPA", "unfpa inter fund": "UNFPA",
    "africa cdc": "Africa CDC", "africa cdc regional investment": "Africa CDC",
    "cdc usa": "CDC USA", "cdc-hiv": "CDC USA", "cdc blood safety": "CDC USA",
    "cdc cop": "CDC COP", "cdc-cop": "CDC COP",
    "cdc international fund": "CDC International Fund", "cdc inter fund": "CDC International Fund",
    "global fund tb": "GF TB", "gf tb": "GF TB",
    "global fund hiv": "GF HIV", "gf hiv": "GF HIV",
    "global fund malaria": "GF Malaria", "gf malaria": "GF Malaria",
    "global fund rssh": "GF RSSH", "gf rssh": "GF RSSH",
    "gavi hss": "GAVI HSS", "gavi covid": "GAVI Covid",
}

AGENCY_ALIASES = {
    "epsa": "EPSA", "ethiopian pharmaceuticals supply agency": "EPSA",
    "ehia": "EHIA", "ethiopia health insurance(ehia)": "EHIA",
    "ephi": "EPHI", "ethiopia public health institute": "EPHI",
    "ethiopian public health institute": "EPHI",
    "ahri": "AHRI", "efda": "EFDA",
    "ethiopia blood bank": "Ethiopia Blood Bank",
    "ethiopian midwives association": "Ethiopian Midwives Association",
    "ethiopian nurses association": "Ethiopian Nurses Association",
}

UNIVERSITY_KEYWORDS = ["university", "univercity", "univeristy"]
HOSPITAL_KEYWORDS = ["hospital", "referal hospital", "specialized hospital", "medical college"]

SUFFIX_PATTERNS = [
    r'\bHAPCO\b', r'\bUNICEF\b', r'\bWHO\b', r'\bUNFPA\b', r'\bUNAIDS\b',
    r'-UN[A-Z]*', r'\(UN[A-Z]*\)', r'\(WHO\)',
]


def _normalize(text_value: str) -> str:
    if not isinstance(text_value, str):
        return ""
    t = text_value.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def _clean_name(name: str) -> str:
    """Strip known donor/agency suffixes off the end of a name, matching the
    notebook's clean_name() behaviour."""
    if not isinstance(name, str):
        return ""
    cleaned = name.strip()
    parts = re.split(r"\s*-\s*", cleaned)
    if len(parts) > 1:
        last = parts[-1]
        if any(re.fullmatch(pat, last, flags=re.IGNORECASE) for pat in SUFFIX_PATTERNS):
            cleaned = "-".join(parts[:-1]).strip()
    return cleaned


def classify_customer_name(raw_name: str):
    """
    Returns (category, standardized_display_name).
    category is one of: "region", "donor", "agency", "university", "hospital", or None
    if nothing matched (in which case it should be reviewed/set manually).
    """
    if not raw_name or not str(raw_name).strip():
        return None, raw_name

    cleaned = _clean_name(str(raw_name))
    norm = _normalize(cleaned)

    if norm in REGION_ALIASES:
        return "region", REGION_ALIASES[norm].title()
    if norm in DONOR_ALIASES:
        return "donor", DONOR_ALIASES[norm]
    if norm in AGENCY_ALIASES:
        return "agency", AGENCY_ALIASES[norm]
    if any(kw in norm for kw in UNIVERSITY_KEYWORDS):
        return "university", cleaned
    if any(kw in norm for kw in HOSPITAL_KEYWORDS):
        return "hospital", cleaned

    return None, cleaned