"""
Gregorian <-> Ethiopian calendar conversion + Ethiopian Fiscal Year/Quarter logic.
Verified against known reference points:
  2024-09-11 (Gregorian) -> Meskerem 1, 2017 (Ethiopian New Year)
  2025-07-08 (Gregorian) -> Hamle 1, 2017 (Ethiopian Fiscal Year start)
"""
from datetime import date, timedelta

ETHIOPIAN_MONTHS = [
    "Meskerem", "Tikimt", "Hidar", "Tahsas", "Tir", "Yekatit",
    "Megabit", "Miazia", "Ginbot", "Sene", "Hamle", "Nehase", "Pagume",
]


def gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def jdn_to_ethiopian(jdn: int):
    r = (jdn - 1723856) % 1461
    n = (r % 365) + 365 * (r // 1460)
    year = 4 * ((jdn - 1723856) // 1461) + (r // 365) - (r // 1460)
    month = n // 30 + 1
    day = n % 30 + 1
    return int(year), int(month), int(day)


def gregorian_to_ethiopian(g_date: date):
    jdn = gregorian_to_jdn(g_date.year, g_date.month, g_date.day)
    return jdn_to_ethiopian(jdn)


def ethiopian_fiscal_year_and_quarter(e_year: int, e_month: int):
    if e_month >= 11:
        return e_year + 1, 1
    elif e_month <= 3:
        return e_year, 2
    elif e_month <= 6:
        return e_year, 3
    else:
        return e_year, 4


def generate_calendar_rows(start_year: int, end_year: int):
    d = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    while d <= end:
        e_year, e_month, e_day = gregorian_to_ethiopian(d)
        fiscal_year, quarter = ethiopian_fiscal_year_and_quarter(e_year, e_month)
        month_name = ETHIOPIAN_MONTHS[e_month - 1] if 1 <= e_month <= 13 else "Unknown"
        yield {
            "gregorian_date": d.isoformat(), "ethiopian_year": e_year, "ethiopian_month": e_month,
            "ethiopian_month_name": month_name, "ethiopian_day": e_day,
            "ethiopian_fiscal_year": fiscal_year, "ethiopian_fiscal_quarter": quarter,
        }
        d += timedelta(days=1)