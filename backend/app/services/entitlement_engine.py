"""M04 — Entitlement Master Engine (spec section 7).

Parsing is a pure function over already-extracted rows + a confirmed column mapping —
no database, no FastAPI — so 'preserve exact sequence' is something a unit test can
pin down exactly (see tests/test_entitlement_engine.py).

Group boundaries are detected by change in the resolved group name across
consecutive material rows, with forward-fill for blank group cells: real entitlement
sheets merge the group-name cell down the block, so openpyxl (which only populates the
top-left cell of a merge) sees blanks on every row after the first. Forward-filling is
what recovers the group each item actually belongs to, rather than misreading merged
cells as N one-item groups.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.services.excel_intelligence import ParsedRow
from app.services.numeric import to_decimal, to_text


@dataclass
class ParsedEntitlementItem:
    row_number: int
    sequence_no: int
    material_name: str
    hs_code: str
    entitlement_unit: str
    annual_entitlement_qty: Decimal
    enhanced_entitlement_qty: Decimal
    total_entitlement_qty: Decimal
    source_sequence_no_raw: str | None = None


@dataclass
class ParsedEntitlementGroup:
    sequence_no: int
    group_name: str
    group_code: str | None
    items: list[ParsedEntitlementItem] = field(default_factory=list)


def parse_entitlement_rows(rows: list[ParsedRow], column_mapping: dict[str, str]) -> list[ParsedEntitlementGroup]:
    """`column_mapping` maps raw spreadsheet header -> canonical target field
    (the confirmed mapping from M03), e.g. {'Material Name': 'material_name', ...}."""
    groups: list[ParsedEntitlementGroup] = []
    last_group_name: str | None = None
    last_group_code: str | None = None

    for row in rows:
        mapped = {target: row.values.get(header) for header, target in column_mapping.items()}

        raw_group_name = to_text(mapped.get("group_name"))
        raw_group_code = to_text(mapped.get("group_code"))
        material_name = to_text(mapped.get("material_name"))

        if raw_group_name:
            last_group_name = raw_group_name
            last_group_code = raw_group_code

        if material_name is None:
            continue  # a section/title/blank row — not an entitlement item

        group_name = raw_group_name or last_group_name or "Ungrouped"
        group_code = raw_group_code or last_group_code

        if not groups or groups[-1].group_name != group_name:
            groups.append(
                ParsedEntitlementGroup(sequence_no=len(groups) + 1, group_name=group_name, group_code=group_code)
            )
        group = groups[-1]

        annual = to_decimal(mapped.get("annual_entitlement_qty")) or Decimal("0")
        enhanced = to_decimal(mapped.get("enhanced_entitlement_qty")) or Decimal("0")

        group.items.append(
            ParsedEntitlementItem(
                row_number=row.row_number,
                sequence_no=len(group.items) + 1,
                material_name=material_name,
                hs_code=to_text(mapped.get("hs_code")) or "",
                entitlement_unit=to_text(mapped.get("entitlement_unit")) or "",
                annual_entitlement_qty=annual,
                enhanced_entitlement_qty=enhanced,
                total_entitlement_qty=annual + enhanced,
                source_sequence_no_raw=to_text(mapped.get("sequence_no")),
            )
        )

    return groups
