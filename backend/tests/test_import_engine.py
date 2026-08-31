from datetime import date
from decimal import Decimal

from app.services.excel_intelligence import ParsedRow
from app.services.import_engine import filter_to_audit_period, parse_import_rows

COLUMN_MAPPING = {
    "BE No": "be_number",
    "BE Date": "be_date",
    "Import Date": "import_date",
    "Description": "item_description",
    "HS Code": "hs_code",
    "Quantity": "declared_quantity",
    "Unit": "declared_unit",
    "Currency": "original_currency",
    "Value": "original_currency_value",
}


def _row(row_number: int, **values) -> ParsedRow:
    base = {
        "BE No": None,
        "BE Date": None,
        "Import Date": None,
        "Description": None,
        "HS Code": None,
        "Quantity": None,
        "Unit": None,
        "Currency": None,
        "Value": None,
    }
    base.update(values)
    return ParsedRow(row_number=row_number, values=base)


def test_parse_skips_incomplete_rows() -> None:
    rows = [
        _row(2, **{"BE No": "C1", "Description": "Item", "HS Code": "1111", "Quantity": 100}),
        _row(3, **{"BE No": "Total"}),  # subtotal row, missing required fields
    ]
    parsed = parse_import_rows(rows, COLUMN_MAPPING)
    assert len(parsed) == 1
    assert parsed[0].be_number == "C1"
    assert parsed[0].declared_quantity == Decimal("100")


def test_filter_to_audit_period_uses_import_date_over_be_date() -> None:
    rows = [
        _row(
            2,
            **{
                "BE No": "C1",
                "BE Date": "2024-12-28",
                "Import Date": "2025-01-05",
                "Description": "Item",
                "HS Code": "1111",
                "Quantity": 100,
            },
        )
    ]
    parsed = parse_import_rows(rows, COLUMN_MAPPING)
    in_period, excluded = filter_to_audit_period(parsed, date(2025, 1, 1), date(2025, 1, 31))
    assert len(in_period) == 1
    assert len(excluded) == 0


def test_filter_to_audit_period_excludes_out_of_range() -> None:
    rows = [
        _row(2, **{"BE No": "C1", "BE Date": "2024-11-01", "Description": "Item", "HS Code": "1111", "Quantity": 100}),
        _row(3, **{"BE No": "C2", "BE Date": "2025-01-15", "Description": "Item", "HS Code": "1111", "Quantity": 50}),
    ]
    parsed = parse_import_rows(rows, COLUMN_MAPPING)
    in_period, excluded = filter_to_audit_period(parsed, date(2025, 1, 1), date(2025, 1, 31))
    assert [t.be_number for t in in_period] == ["C2"]
    assert [t.be_number for t in excluded] == ["C1"]


def test_filter_excludes_transactions_with_no_usable_date() -> None:
    rows = [_row(2, **{"BE No": "C1", "Description": "Item", "HS Code": "1111", "Quantity": 100})]
    parsed = parse_import_rows(rows, COLUMN_MAPPING)
    in_period, excluded = filter_to_audit_period(parsed, date(2025, 1, 1), date(2025, 1, 31))
    assert in_period == []
    assert len(excluded) == 1
