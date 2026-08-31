from datetime import date
from decimal import Decimal

from app.models.enums import ExcessStatus
from app.services.excess_engine import ExcessLineInput, compute_chronological_excess


def test_spec_partial_excess_worked_example() -> None:
    """Spec section 14's exact numbers: 10,000 approved, 9,500 then 1,000 imported
    chronologically -> 500 allowed / 500 excess on the second B/E."""
    lines = [
        ExcessLineInput(transaction_id="t1", be_date=date(2025, 1, 5), be_number="C1", entitlement_quantity=Decimal("9500")),
        ExcessLineInput(transaction_id="t2", be_date=date(2025, 1, 15), be_number="C2", entitlement_quantity=Decimal("1000")),
    ]
    results = compute_chronological_excess(lines, Decimal("10000"))

    assert results[0].excess_status == ExcessStatus.WITHIN_ENTITLEMENT
    assert results[0].allowed_quantity == Decimal("9500")
    assert results[0].excess_quantity == Decimal("0")
    assert results[0].cumulative_quantity_after == Decimal("9500")

    assert results[1].excess_status == ExcessStatus.PARTIAL_EXCESS
    assert results[1].allowed_quantity == Decimal("500")
    assert results[1].excess_quantity == Decimal("500")
    assert results[1].cumulative_quantity_after == Decimal("10500")


def test_full_excess_after_entitlement_already_exhausted() -> None:
    lines = [
        ExcessLineInput(transaction_id="t1", be_date=date(2025, 1, 1), be_number="C1", entitlement_quantity=Decimal("10000")),
        ExcessLineInput(transaction_id="t2", be_date=date(2025, 1, 20), be_number="C2", entitlement_quantity=Decimal("2000")),
    ]
    results = compute_chronological_excess(lines, Decimal("10000"))
    assert results[0].excess_status == ExcessStatus.WITHIN_ENTITLEMENT
    assert results[1].excess_status == ExcessStatus.FULL_EXCESS
    assert results[1].allowed_quantity == Decimal("0")
    assert results[1].excess_quantity == Decimal("2000")


def test_processes_out_of_order_input_chronologically() -> None:
    lines = [
        ExcessLineInput(transaction_id="later", be_date=date(2025, 1, 20), be_number="C2", entitlement_quantity=Decimal("1000")),
        ExcessLineInput(transaction_id="earlier", be_date=date(2025, 1, 5), be_number="C1", entitlement_quantity=Decimal("9500")),
    ]
    results = compute_chronological_excess(lines, Decimal("10000"))
    assert [r.transaction_id for r in results] == ["earlier", "later"]


def test_exactly_at_entitlement_boundary_is_within() -> None:
    lines = [ExcessLineInput(transaction_id="t1", be_date=date(2025, 1, 1), be_number="C1", entitlement_quantity=Decimal("10000"))]
    results = compute_chronological_excess(lines, Decimal("10000"))
    assert results[0].excess_status == ExcessStatus.WITHIN_ENTITLEMENT
    assert results[0].excess_quantity == Decimal("0")


def test_multiple_be_numbers_same_date_use_be_number_as_tiebreak() -> None:
    lines = [
        ExcessLineInput(transaction_id="b", be_date=date(2025, 1, 5), be_number="C2", entitlement_quantity=Decimal("1000")),
        ExcessLineInput(transaction_id="a", be_date=date(2025, 1, 5), be_number="C1", entitlement_quantity=Decimal("9500")),
    ]
    results = compute_chronological_excess(lines, Decimal("10000"))
    assert [r.transaction_id for r in results] == ["a", "b"]
    assert results[1].excess_status == ExcessStatus.PARTIAL_EXCESS
