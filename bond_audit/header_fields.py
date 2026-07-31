"""Best-effort extraction of the key/value header block above the table
(Ex-Bond No & Date, Export Qty, Export Value, C&F Agent, etc).

The label column in these scans is often a rotated customs stamp overlapping
the printed labels, so labels OCR unreliably. Values are extracted from the
full-page OCR text by pattern rather than by matching a label, and the raw
OCR text is always kept in OCR_OUTPUT for manual cross-check.
"""
from __future__ import annotations

import re

_EX_BOND_RE = re.compile(r"Ex-?Bond\s*No\.?\s*&?\s*Date\W*", re.IGNORECASE)
_QTY_RE = re.compile(r"([\d,]+)\s*(?:PCS|PC)\b", re.IGNORECASE)
_VALUE_RE = re.compile(r"\$\s?[\d,]+\.\d{2}")
_CF_AGENT_RE = re.compile(r"^.*(Cargo|Logistics|Shipping|Freight).*$", re.IGNORECASE | re.MULTILINE)


def extract_header_fields(full_text: str) -> dict:
    fields: dict = {}

    m = _EX_BOND_RE.search(full_text)
    if m:
        tail = full_text[m.end(): m.end() + 60].strip().splitlines()
        if tail:
            fields["ex_bond_no_date"] = tail[0].strip()

    m = _QTY_RE.search(full_text)
    if m:
        fields["export_qty"] = m.group(0).strip()

    m = _VALUE_RE.search(full_text)
    if m:
        fields["export_value"] = m.group(0).strip()

    m = _CF_AGENT_RE.search(full_text)
    if m:
        fields["cf_agent"] = m.group(0).strip()

    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    for ln in lines[:6]:
        if "LIMITED" in ln.upper() and "company_name" not in fields:
            fields["company_name"] = ln.lstrip(": ").strip()

    return fields
