"""Shared, defensive parsing for values pulled out of spreadsheet cells.

Centralized so every engine treats a blank/unparsable cell the same way: return None
rather than guessing a default, so the caller can decide to flag the row for review
instead of silently substituting zero (spec section 3: 'flag the record for review
rather than guessing')."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation


def to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d %B %Y", "%d.%m.%Y")


def to_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        return None
    return None


def to_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def json_safe_row(values: dict) -> dict:
    """Convert a raw spreadsheet row (openpyxl cell values: str/int/float/datetime/None)
    into something a JSON column can store verbatim, without losing any value —
    this is the Layer A raw-evidence payload, so nothing here may be dropped."""
    safe: dict = {}
    for key, value in values.items():
        if isinstance(value, Decimal):
            safe[key] = str(value)
        elif isinstance(value, (datetime, date)):
            safe[key] = value.isoformat()
        else:
            safe[key] = value
    return safe
