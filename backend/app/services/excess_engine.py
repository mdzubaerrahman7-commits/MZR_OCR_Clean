"""M08 — Excess Import Engine (spec section 14).

Processes one entitlement item's approved, converted transactions in chronological
Bill of Entry order, carrying a running cumulative entitlement-unit quantity. A
single transaction that straddles the entitlement ceiling is split into an allowed
portion and an excess portion — this is the literal 'partial excess within a Bill of
Entry' worked example in the spec:

    Approved Entitlement: 10,000 KG
    Previous cumulative import: 9,500 KG
    Current B/E import: 1,000 KG
    Allowed portion: 500 KG
    Excess portion: 500 KG

which `test_excess_engine.py` pins down exactly.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.enums import ExcessStatus


@dataclass(frozen=True)
class ExcessLineInput:
    transaction_id: str
    be_date: date
    be_number: str
    entitlement_quantity: Decimal


@dataclass
class ExcessLineResult:
    transaction_id: str
    excess_status: ExcessStatus
    allowed_quantity: Decimal
    excess_quantity: Decimal
    cumulative_quantity_after: Decimal


def compute_chronological_excess(
    lines: list[ExcessLineInput], total_entitlement_qty: Decimal
) -> list[ExcessLineResult]:
    """`lines` need not already be sorted — chronological order (be_date, then
    be_number as a stable tiebreak) is enforced here so the caller can't accidentally
    process transactions out of order."""
    ordered = sorted(lines, key=lambda line: (line.be_date, line.be_number, line.transaction_id))

    cumulative = Decimal("0")
    results: list[ExcessLineResult] = []
    for line in ordered:
        new_cumulative = cumulative + line.entitlement_quantity

        if new_cumulative <= total_entitlement_qty:
            allowed = line.entitlement_quantity
            excess = Decimal("0")
            status = ExcessStatus.WITHIN_ENTITLEMENT
        elif cumulative >= total_entitlement_qty:
            allowed = Decimal("0")
            excess = line.entitlement_quantity
            status = ExcessStatus.FULL_EXCESS
        else:
            allowed = total_entitlement_qty - cumulative
            excess = new_cumulative - total_entitlement_qty
            status = ExcessStatus.PARTIAL_EXCESS

        results.append(
            ExcessLineResult(
                transaction_id=line.transaction_id,
                excess_status=status,
                allowed_quantity=allowed,
                excess_quantity=excess,
                cumulative_quantity_after=new_cumulative,
            )
        )
        cumulative = new_cumulative

    return results
