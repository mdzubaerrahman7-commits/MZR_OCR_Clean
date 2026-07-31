"""Turn a detected table grid into structured bond consumption report rows."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .grid import Grid
from .ocr_engine import ocr_cell

# Canonical column name -> keywords looked for in the OCR'd header cell text.
COLUMN_KEYWORDS: list[tuple[str, list[str]]] = [
    ("in_bond_no_date", ["bond"]),
    ("import_cno_date", ["import"]),
    ("office_code", ["office"]),
    ("item_no", ["item"]),
    ("material_name", ["material", "raw"]),
    ("unit", ["unit"]),
    ("opening_qty", ["opening"]),
    ("consumption_with_wastage", ["wastage"]),
    ("consumption_asycuda", ["asycuda"]),
    ("closing_qty", ["closing"]),
    ("sl_no", ["sl"]),
]

NUMERIC_COLUMNS = (
    "opening_qty",
    "consumption_with_wastage",
    "consumption_asycuda",
    "closing_qty",
)

DIGIT_WHITELIST = "0123456789.,-"
OCR_SCALES = (3, 4, 5)

_NUMBER_RE = re.compile(r"[-+]?[\d,]*\.?\d+")


def parse_number(text: str) -> float | None:
    """Best-effort parse of an OCR'd quantity cell, e.g. '11,426.78', 'NIL', ''.

    Every quantity in this report has exactly 2 decimal places. Tesseract
    occasionally mis-recognizes the decimal point as a comma (e.g. '1.32' ->
    '1,32', or '2,145.00' -> '2,145,00'). A real thousands-separator comma is
    never the last one in a 2-decimal-place number, so if the number has no
    period and its final comma is followed by exactly 2 digits, that comma is
    treated as the misread decimal point; any earlier commas are left as
    thousands separators and stripped normally.
    """
    if not text:
        return None
    cleaned = text.strip().upper()
    alpha_only = "".join(ch for ch in cleaned if ch.isalpha())
    if cleaned in {"-", "--"} or alpha_only in {"NIL", "NIE", "NII", "NL"}:
        return 0.0
    match = _NUMBER_RE.search(text.replace(" ", ""))
    if not match:
        return None
    number = match.group(0)
    if "." not in number and "," in number:
        before, after = number.rsplit(",", 1)
        if len(after) == 2:
            number = f"{before}.{after}"
    try:
        return float(number.replace(",", ""))
    except ValueError:
        return None


def _ocr_numeric_cell(gray, y0: int, y1: int, x0: int, x1: int) -> str:
    """OCR a quantity cell at a few render scales and take the value at least
    two of them agree on, falling back to the smallest scale's reading.
    Single-scale OCR on these low-resolution scans intermittently drops or
    duplicates a digit; a scale where two independent renders agree is much
    more likely to be the true value than any one of them alone.
    """
    readings: list[tuple[str, float | None]] = []
    for scale in OCR_SCALES:
        text = ocr_cell(gray, y0, y1, x0, x1, psm=7, whitelist=DIGIT_WHITELIST, scale=scale)
        readings.append((text, parse_number(text)))

    values = [v for _, v in readings if v is not None]
    for v in values:
        if values.count(v) >= 2:
            idx = next(i for i, (_, rv) in enumerate(readings) if rv == v)
            return readings[idx][0]

    if readings[0][1] is not None:
        return readings[0][0]

    # No scale produced a parseable number - likely non-numeric ("NIL"); retry unrestricted.
    return ocr_cell(gray, y0, y1, x0, x1, psm=7)


def _match_column(header_text: str, used: set[str]) -> str | None:
    """Match a header cell to the first not-yet-used canonical column whose
    keyword list has any hit in the (OCR'd, noisy) header text.
    """
    lowered = header_text.lower()
    for canonical, keywords in COLUMN_KEYWORDS:
        if canonical in used:
            continue
        if any(k in lowered for k in keywords):
            used.add(canonical)
            return canonical
    return None


@dataclass
class ExtractedTable:
    columns: list[str]  # canonical column name per grid column, "" if unmapped
    rows: list[dict] = field(default_factory=list)
    unmapped_header_cells: list[str] = field(default_factory=list)


def extract_table(gray, grid: Grid) -> ExtractedTable:
    """OCR every cell in the grid and assemble rows keyed by canonical column name.

    The header band is grid row 0. Each subsequent row becomes one report line
    item. Columns are identified by matching header text against known
    keywords rather than a fixed index, so the extractor tolerates minor
    column-count drift between scans.
    """
    used: set[str] = set()
    columns: list[str] = []
    unmapped: list[str] = []

    header_y0, header_y1 = grid.row_lines[0], grid.row_lines[1]
    for c in range(grid.n_cols):
        x0, x1 = grid.col_lines[c], grid.col_lines[c + 1]
        header_text = ocr_cell(gray, header_y0, header_y1, x0, x1)
        canonical = _match_column(header_text, used)
        if canonical is None:
            unmapped.append(header_text)
            columns.append("")
        else:
            columns.append(canonical)

    rows: list[dict] = []
    for r in range(1, grid.n_rows):
        y0, y1 = grid.row_lines[r], grid.row_lines[r + 1]
        row: dict = {}
        for c, canonical in enumerate(columns):
            if not canonical:
                continue
            x0, x1 = grid.col_lines[c], grid.col_lines[c + 1]
            if canonical in NUMERIC_COLUMNS:
                text = _ocr_numeric_cell(gray, y0, y1, x0, x1)
            elif canonical == "sl_no":
                text = ocr_cell(gray, y0, y1, x0, x1, psm=7, whitelist=DIGIT_WHITELIST)
                if parse_number(text) is None:
                    text = ocr_cell(gray, y0, y1, x0, x1, psm=7)
            else:
                text = ocr_cell(gray, y0, y1, x0, x1, psm=6)
            row[canonical] = text
        for col in NUMERIC_COLUMNS:
            value = parse_number(row.get(col, ""))
            # Quantities are physically non-negative; a leading '-' this report
            # never intends is consistently a misread stray mark, not a real sign.
            row[f"{col}_value"] = abs(value) if value is not None else None
        rows.append(row)

    return ExtractedTable(columns=columns, rows=rows, unmapped_header_cells=unmapped)
