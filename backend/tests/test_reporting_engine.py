from datetime import date
from decimal import Decimal

from app.services.reporting_engine import (
    ExceptionSummary,
    ReportEntitlementItem,
    ReportFindingLine,
    ReportTransactionLine,
    generate_output_01,
    generate_output_02,
    generate_output_04,
    generate_output_07,
)

ITEM_A = ReportEntitlementItem(
    entitlement_item_id="e1", group_sequence_no=1, group_name="Polymer & Resins", item_sequence_no=1,
    material_name="Polypropylene Resin", hs_code="3902.10.00", entitlement_unit="KG",
    annual_entitlement_qty=Decimal("10000"), enhanced_entitlement_qty=Decimal("0"), total_entitlement_qty=Decimal("10000"),
)
ITEM_B = ReportEntitlementItem(
    entitlement_item_id="e2", group_sequence_no=2, group_name="Packaging Material", item_sequence_no=1,
    material_name="Corrugated Carton", hs_code="4819.10.00", entitlement_unit="PCS",
    annual_entitlement_qty=Decimal("50000"), enhanced_entitlement_qty=Decimal("5000"), total_entitlement_qty=Decimal("55000"),
)

LINE_A = ReportTransactionLine(
    entitlement_item_id="e1", material_name="Polypropylene Resin", hs_code="3902.10.00", be_number="C-0001",
    be_date=date(2025, 1, 5), declared_quantity=Decimal("9500"), declared_unit="KG",
    entitlement_quantity=Decimal("9500"), entitlement_unit="KG", kg_quantity=Decimal("9500"),
    original_currency="USD", original_currency_value=Decimal("47500"), usd_value=Decimal("47500"),
    classification="raw_material",
)


def test_output_01_preserves_group_order_and_writes_subtotals() -> None:
    items = [ITEM_A, ITEM_B]
    lines_by_item = {"e1": [LINE_A]}
    workbook = generate_output_01(items, lines_by_item, "Test Audit")
    sheet = workbook.active

    values = [[cell.value for cell in row] for row in sheet.iter_rows()]
    group_column = [row[0] for row in values if row[0]]
    # First group's rows/subtotal must appear before the second group's.
    assert group_column.index("Polymer & Resins — Subtotal") < len(group_column)
    first_group_idx = next(i for i, v in enumerate(group_column) if v == "Polymer & Resins")
    second_group_idx = next(i for i, v in enumerate(group_column) if v == "Polymer & Resins — Subtotal")
    assert second_group_idx > first_group_idx


def test_output_02_grand_total_row_present() -> None:
    items = [ITEM_A, ITEM_B]
    lines_by_item = {"e1": [LINE_A]}
    workbook = generate_output_02(items, lines_by_item, "Test Audit")
    sheet = workbook.active
    first_column_values = [cell.value for row in sheet.iter_rows() for cell in [row[0]] if cell.value]
    assert "GRAND TOTAL" in first_column_values


def test_output_04_lists_every_control() -> None:
    summary = ExceptionSummary(
        non_entitled_count=2, review_required_match_count=1, unknown_classification_count=0,
        partial_excess_count=1, full_excess_count=0, conversion_incomplete_count=3,
    )
    workbook = generate_output_04(summary, "Test Audit")
    sheet = workbook.active
    counts = [cell.value for row in sheet.iter_rows(min_row=4) for cell in [row[1]] if cell.value is not None]
    assert counts == [2, 1, 0, 1, 0, 3]


def test_output_07_findings_register_rows() -> None:
    findings = [
        ReportFindingLine(
            finding_code="F-0001", issue_type="non_entitled", evidence="evidence text", be_number="C-0001",
            material_name="Unknown Chemical", quantity=Decimal("100"), unit="KG", value=Decimal("500"),
            demand_amount=Decimal("50.00"), review_status="open",
        )
    ]
    workbook = generate_output_07(findings, "Test Audit")
    sheet = workbook.active
    data_row = [cell.value for cell in sheet[4]]
    assert data_row[0] == "F-0001"
    assert data_row[1] == "non_entitled"
