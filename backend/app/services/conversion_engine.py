"""M07 — Quantity & Currency Conversion Engine (spec sections 11-12).

Every conversion here is optional-in, evidence-gated: a result field stays None
unless the specific piece of Bill of Entry evidence needed to compute it exists.
Nothing is ever defaulted to 1.0 or guessed — a missing factor means the field is
null and the transaction is flagged REVIEW_REQUIRED by the caller, not silently
approximated (spec section 11: 'Do not use an assumed conversion factor when B/E
evidence is required'; section 12: 'Do not substitute a current market exchange
rate').
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class BillOfEntryEvidence:
    exchange_rate: Decimal | None
    exchange_rate_evidence: str | None
    kg_conversion_factor: Decimal | None
    kg_conversion_evidence: str | None
    entitlement_conversion_factor: Decimal | None
    entitlement_conversion_evidence: str | None


@dataclass
class ConversionResult:
    entitlement_quantity: Decimal | None
    kg_quantity: Decimal | None
    usd_value: Decimal | None
    evidence_notes: list[str]
    fully_converted: bool


def convert_transaction(
    *,
    declared_quantity: Decimal,
    declared_unit: str,
    entitlement_unit: str | None,
    original_currency: str | None,
    original_currency_value: Decimal | None,
    be_evidence: BillOfEntryEvidence | None,
) -> ConversionResult:
    notes: list[str] = []

    # --- Entitlement-unit quantity ---
    entitlement_quantity: Decimal | None
    if entitlement_unit is None:
        entitlement_quantity = None
        notes.append("No matched entitlement item yet — entitlement-unit quantity cannot be computed.")
    elif _units_equivalent(declared_unit, entitlement_unit):
        entitlement_quantity = declared_quantity
    elif be_evidence and be_evidence.entitlement_conversion_factor is not None:
        entitlement_quantity = declared_quantity * be_evidence.entitlement_conversion_factor
        notes.append(be_evidence.entitlement_conversion_evidence or "B/E entitlement-unit conversion factor applied.")
    else:
        entitlement_quantity = None
        notes.append(
            f"declared_unit '{declared_unit}' != entitlement_unit '{entitlement_unit}' and no B/E conversion "
            "factor is on file — quantity conversion withheld rather than assumed."
        )

    # --- KG quantity ---
    kg_quantity: Decimal | None
    if _units_equivalent(declared_unit, "KG"):
        kg_quantity = declared_quantity
    elif be_evidence and be_evidence.kg_conversion_factor is not None:
        kg_quantity = declared_quantity * be_evidence.kg_conversion_factor
        notes.append(be_evidence.kg_conversion_evidence or "B/E KG conversion factor applied.")
    else:
        kg_quantity = None
        notes.append(f"declared_unit '{declared_unit}' is not KG and no B/E KG conversion factor is on file.")

    # --- Currency ---
    usd_value: Decimal | None
    if original_currency_value is None:
        usd_value = None
        notes.append("No original currency value on the source row — USD value withheld.")
    elif _is_usd(original_currency):
        usd_value = original_currency_value
    elif be_evidence and be_evidence.exchange_rate is not None:
        usd_value = original_currency_value * be_evidence.exchange_rate
        notes.append(be_evidence.exchange_rate_evidence or "B/E exchange rate applied.")
    else:
        usd_value = None
        notes.append(
            f"original_currency '{original_currency}' is not USD and no B/E exchange rate is on file — "
            "USD value withheld rather than using a market rate."
        )

    fully_converted = entitlement_quantity is not None and kg_quantity is not None and usd_value is not None
    return ConversionResult(
        entitlement_quantity=entitlement_quantity,
        kg_quantity=kg_quantity,
        usd_value=usd_value,
        evidence_notes=notes,
        fully_converted=fully_converted,
    )


def _units_equivalent(unit_a: str | None, unit_b: str | None) -> bool:
    if not unit_a or not unit_b:
        return False
    return unit_a.strip().casefold() == unit_b.strip().casefold()


def _is_usd(currency: str | None) -> bool:
    return (currency or "").strip().upper() in {"USD", "US$", "$"}
