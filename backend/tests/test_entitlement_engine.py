from decimal import Decimal

from app.services.entitlement_engine import parse_entitlement_rows
from app.services.excel_intelligence import ParsedRow

COLUMN_MAPPING = {
    "Group": "group_name",
    "SL": "sequence_no",
    "Material": "material_name",
    "HS Code": "hs_code",
    "Unit": "entitlement_unit",
    "Annual": "annual_entitlement_qty",
    "Enhanced": "enhanced_entitlement_qty",
}


def _row(row_number: int, group, sl, material, hs, unit, annual, enhanced) -> ParsedRow:
    return ParsedRow(
        row_number=row_number,
        values={
            "Group": group,
            "SL": sl,
            "Material": material,
            "HS Code": hs,
            "Unit": unit,
            "Annual": annual,
            "Enhanced": enhanced,
        },
    )


def test_forward_fills_merged_group_cells() -> None:
    # Simulates a merged 'Group' cell: openpyxl only populates the first row of the merge.
    rows = [
        _row(5, "Polymer & Resins", 1, "Polypropylene", "3902.10", "KG", 10000, 0),
        _row(6, None, 2, "Polyethylene", "3901.10", "KG", 8000, 0),
        _row(7, "Packaging Material", 1, "Corrugated Carton", "4819.10", "PCS", 50000, 5000),
    ]
    groups = parse_entitlement_rows(rows, COLUMN_MAPPING)

    assert [g.group_name for g in groups] == ["Polymer & Resins", "Packaging Material"]
    assert [g.sequence_no for g in groups] == [1, 2]
    assert len(groups[0].items) == 2
    assert len(groups[1].items) == 1


def test_preserves_item_sequence_within_group() -> None:
    rows = [
        _row(2, "G1", 1, "Item A", "1111", "KG", 100, 0),
        _row(3, None, 2, "Item B", "2222", "KG", 200, 0),
        _row(4, None, 3, "Item C", "3333", "KG", 300, 0),
    ]
    groups = parse_entitlement_rows(rows, COLUMN_MAPPING)
    assert len(groups) == 1
    names = [item.material_name for item in groups[0].items]
    assert names == ["Item A", "Item B", "Item C"]
    assert [item.sequence_no for item in groups[0].items] == [1, 2, 3]


def test_total_entitlement_is_annual_plus_enhanced() -> None:
    rows = [_row(2, "G1", 1, "Item A", "1111", "KG", "10,000.50", 500)]
    groups = parse_entitlement_rows(rows, COLUMN_MAPPING)
    item = groups[0].items[0]
    assert item.annual_entitlement_qty == Decimal("10000.50")
    assert item.enhanced_entitlement_qty == Decimal("500")
    assert item.total_entitlement_qty == Decimal("10500.50")


def test_blank_material_row_is_skipped_but_still_updates_group() -> None:
    rows = [
        _row(2, "G1", None, None, None, None, None, None),  # section title only
        _row(3, None, 1, "Item A", "1111", "KG", 100, 0),
    ]
    groups = parse_entitlement_rows(rows, COLUMN_MAPPING)
    assert len(groups) == 1
    assert groups[0].group_name == "G1"
    assert len(groups[0].items) == 1


def test_reappearing_group_name_creates_a_new_block_not_a_merge() -> None:
    """A non-contiguous repeat of a group name must not be silently merged into the
    earlier block — that would reorder/hide data relative to the source file."""
    rows = [
        _row(2, "G1", 1, "Item A", "1111", "KG", 100, 0),
        _row(3, "G2", 1, "Item B", "2222", "KG", 100, 0),
        _row(4, "G1", 2, "Item C", "3333", "KG", 100, 0),
    ]
    groups = parse_entitlement_rows(rows, COLUMN_MAPPING)
    assert [g.group_name for g in groups] == ["G1", "G2", "G1"]
