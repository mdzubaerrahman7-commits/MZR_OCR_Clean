"""M09 — Duty & Demand Assessment Engine (spec section 9).

Duty components (CD/RD/SD/VAT/AIT/AT/...) are entered against a Bill of Entry from
the auditor's own evidence (bill_of_entries router), never invented here — this
module only prorates that already-evidenced total duty across the portion of a
transaction's quantity that is non-entitled or in excess. The spec doesn't specify a
compound-duty cascade formula, so a straight quantity-ratio proration of the B/E's
total assessed duty is the reproducible, evidence-only method: it never invents a
tax rate or a cascade the auditor didn't enter.
"""

from decimal import ROUND_HALF_UP, Decimal


def prorated_demand(total_be_duty: Decimal | None, portion_quantity: Decimal, declared_quantity: Decimal) -> Decimal | None:
    """Demand attributable to `portion_quantity` out of a transaction's
    `declared_quantity`, as that same fraction of the Bill of Entry's total assessed
    duty. Returns None (not zero) when there's no duty evidence to prorate — a
    finding with unknown demand must say so, not silently claim BDT 0."""
    if total_be_duty is None:
        return None
    if declared_quantity == 0:
        return Decimal("0.00")
    ratio = portion_quantity / declared_quantity
    return (total_be_duty * ratio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def sum_duty_components(calculated_amounts: list[Decimal]) -> Decimal:
    total = Decimal("0")
    for amount in calculated_amounts:
        total += amount
    return total
