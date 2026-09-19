import re
import pandas as pd
from dateutil import parser as dateparser


def normalize_text(val):
    """Turn blanks/N-A-like strings into real None."""
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() in {"n/a", "na", "-", "none", "null"}:
        return None
    return s


def normalize_date(val):
    """Parse messy date strings into ISO format (YYYY-MM-DD), or None if unparseable."""
    s = normalize_text(val)
    if s is None:
        return None
    try:
        return dateparser.parse(s, fuzzy=True).date().isoformat()
    except Exception:
        return None


def normalize_amount(val):
    """Strip currency symbols/commas and convert to float, or None if unparseable."""
    s = normalize_text(val)
    if s is None:
        return None
    cleaned = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(cleaned) if cleaned not in ("", "-", ".") else None
    except ValueError:
        return None


def normalize_sector(val):
    """Normalize casing/whitespace for sector/category-like text fields."""
    s = normalize_text(val)
    if s is None:
        return None
    return s.strip().title()


def data_quality_report(df: pd.DataFrame, columns: list[str]) -> dict:
    """Return {column: {'missing': count, 'missing_pct': pct}} for given columns."""
    report = {}
    total = len(df)
    for col in columns:
        if col not in df.columns:
            continue
        missing = df[col].isna().sum()
        report[col] = {
            "missing": int(missing),
            "missing_pct": round(missing / total * 100, 1) if total else 0.0,
        }
    return report


if __name__ == "__main__":
    # quick sanity tests
    print(normalize_text(""))          # None
    print(normalize_text("  N/A "))    # None
    print(normalize_text("Mining"))    # "Mining"
    print(normalize_date("12/31/2025"))
    print(normalize_date("garbage"))
    print(normalize_amount('"264398.08"'))
    print(normalize_amount(""))
    print(normalize_sector("  mining "))