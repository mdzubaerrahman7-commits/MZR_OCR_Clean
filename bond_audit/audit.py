"""Reconciliation checks for bond consumption report line items.

The report's own arithmetic invariant is:

    Closing Qty == Opening Qty - Consumption (with wastage)

This module verifies that invariant per row and flags anything that fails it
or that OCR could not confidently extract, so a human only has to look at the
exceptions rather than the whole document.
"""
from __future__ import annotations

from dataclasses import dataclass

TOLERANCE = 0.05  # absolute quantity tolerance to absorb rounding/OCR jitter


@dataclass
class RowAudit:
    row_index: int
    material_name: str
    status: str  # "OK", "MISMATCH", "INCOMPLETE"
    opening_qty: float | None
    consumption_with_wastage: float | None
    closing_qty: float | None
    expected_closing_qty: float | None
    variance: float | None
    notes: str


def audit_row(index: int, row: dict) -> RowAudit:
    opening = row.get("opening_qty_value")
    consumption = row.get("consumption_with_wastage_value")
    closing = row.get("closing_qty_value")
    material = row.get("material_name", "").strip()

    if opening is None or consumption is None or closing is None:
        missing = [
            name
            for name, val in (
                ("opening_qty", opening),
                ("consumption_with_wastage", consumption),
                ("closing_qty", closing),
            )
            if val is None
        ]
        return RowAudit(
            row_index=index,
            material_name=material,
            status="INCOMPLETE",
            opening_qty=opening,
            consumption_with_wastage=consumption,
            closing_qty=closing,
            expected_closing_qty=None,
            variance=None,
            notes=f"OCR could not read: {', '.join(missing)}",
        )

    expected_closing = opening - consumption
    variance = closing - expected_closing
    if abs(variance) <= TOLERANCE:
        return RowAudit(
            row_index=index,
            material_name=material,
            status="OK",
            opening_qty=opening,
            consumption_with_wastage=consumption,
            closing_qty=closing,
            expected_closing_qty=expected_closing,
            variance=variance,
            notes="",
        )

    return RowAudit(
        row_index=index,
        material_name=material,
        status="MISMATCH",
        opening_qty=opening,
        consumption_with_wastage=consumption,
        closing_qty=closing,
        expected_closing_qty=expected_closing,
        variance=variance,
        notes=f"Closing Qty differs from Opening - Consumption by {variance:+.2f}",
    )


def audit_rows(rows: list[dict]) -> list[RowAudit]:
    return [audit_row(i + 1, row) for i, row in enumerate(rows)]
