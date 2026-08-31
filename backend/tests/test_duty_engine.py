from decimal import Decimal

from app.services.duty_engine import prorated_demand, sum_duty_components


def test_prorated_demand_full_quantity_equals_total_duty() -> None:
    assert prorated_demand(Decimal("10000.00"), Decimal("500"), Decimal("500")) == Decimal("10000.00")


def test_prorated_demand_half_quantity() -> None:
    assert prorated_demand(Decimal("10000.00"), Decimal("250"), Decimal("500")) == Decimal("5000.00")


def test_prorated_demand_none_when_no_duty_evidence() -> None:
    assert prorated_demand(None, Decimal("250"), Decimal("500")) is None


def test_prorated_demand_zero_declared_quantity_is_zero_not_error() -> None:
    assert prorated_demand(Decimal("10000.00"), Decimal("0"), Decimal("0")) == Decimal("0.00")


def test_sum_duty_components() -> None:
    total = sum_duty_components([Decimal("100.50"), Decimal("49.50"), Decimal("0")])
    assert total == Decimal("150.00")
