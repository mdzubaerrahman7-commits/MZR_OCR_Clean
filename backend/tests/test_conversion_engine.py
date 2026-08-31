from decimal import Decimal

from app.services.conversion_engine import BillOfEntryEvidence, convert_transaction


def test_same_unit_needs_no_evidence() -> None:
    result = convert_transaction(
        declared_quantity=Decimal("1000"),
        declared_unit="KG",
        entitlement_unit="KG",
        original_currency="USD",
        original_currency_value=Decimal("5000"),
        be_evidence=None,
    )
    assert result.entitlement_quantity == Decimal("1000")
    assert result.kg_quantity == Decimal("1000")
    assert result.usd_value == Decimal("5000")
    assert result.fully_converted is True


def test_unit_mismatch_without_evidence_is_withheld_not_guessed() -> None:
    result = convert_transaction(
        declared_quantity=Decimal("1000"),
        declared_unit="PCS",
        entitlement_unit="KG",
        original_currency="USD",
        original_currency_value=Decimal("5000"),
        be_evidence=None,
    )
    assert result.entitlement_quantity is None
    assert result.kg_quantity is None
    assert result.fully_converted is False
    assert any("no B/E" in note for note in result.evidence_notes)


def test_unit_mismatch_with_be_evidence_converts() -> None:
    evidence = BillOfEntryEvidence(
        exchange_rate=None,
        exchange_rate_evidence=None,
        kg_conversion_factor=Decimal("0.5"),
        kg_conversion_evidence="B/E C-12345: 1 PCS = 0.5 KG per packing list",
        entitlement_conversion_factor=Decimal("0.5"),
        entitlement_conversion_evidence="B/E C-12345: 1 PCS = 0.5 KG",
    )
    result = convert_transaction(
        declared_quantity=Decimal("1000"),
        declared_unit="PCS",
        entitlement_unit="KG",
        original_currency="USD",
        original_currency_value=Decimal("5000"),
        be_evidence=evidence,
    )
    assert result.entitlement_quantity == Decimal("500.0")
    assert result.kg_quantity == Decimal("500.0")


def test_non_usd_currency_without_rate_withheld() -> None:
    result = convert_transaction(
        declared_quantity=Decimal("1000"),
        declared_unit="KG",
        entitlement_unit="KG",
        original_currency="EUR",
        original_currency_value=Decimal("4500"),
        be_evidence=None,
    )
    assert result.usd_value is None
    assert result.fully_converted is False


def test_non_usd_currency_with_be_exchange_rate_converts() -> None:
    evidence = BillOfEntryEvidence(
        exchange_rate=Decimal("1.08"),
        exchange_rate_evidence="B/E C-12345 assessment sheet exchange rate",
        kg_conversion_factor=None,
        kg_conversion_evidence=None,
        entitlement_conversion_factor=None,
        entitlement_conversion_evidence=None,
    )
    result = convert_transaction(
        declared_quantity=Decimal("1000"),
        declared_unit="KG",
        entitlement_unit="KG",
        original_currency="EUR",
        original_currency_value=Decimal("4500"),
        be_evidence=evidence,
    )
    assert result.usd_value == Decimal("4860.00")


def test_no_matched_entitlement_item_withholds_entitlement_quantity() -> None:
    result = convert_transaction(
        declared_quantity=Decimal("1000"),
        declared_unit="KG",
        entitlement_unit=None,
        original_currency="USD",
        original_currency_value=Decimal("5000"),
        be_evidence=None,
    )
    assert result.entitlement_quantity is None
    assert result.kg_quantity == Decimal("1000")  # KG conversion is independent of matching
