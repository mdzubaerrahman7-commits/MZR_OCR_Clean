"""Import MIS parsing + audit-period filter (spec section 2: 'Extract only
transactions falling within the selected audit period', and section 8's
import_transactions model).

Like the entitlement engine, parsing is a pure function over already-extracted rows
and a confirmed column mapping. The audit-period filter is a second, separate pure
function so 'what counts as in-period' has one unambiguous, testable definition:
`import_date` when present, otherwise `be_date`.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services.excel_intelligence import ParsedRow
from app.services.numeric import to_date, to_decimal, to_text


@dataclass
class ParsedImportTransaction:
    row_number: int
    be_number: str
    be_date: date | None
    import_date: date | None
    lc_number: str | None
    invoice_number: str | None
    item_description: str
    hs_code: str
    declared_quantity: Decimal
    declared_unit: str
    original_currency: str | None
    original_currency_value: Decimal | None
    raw_values: dict

    @property
    def transaction_date(self) -> date | None:
        return self.import_date or self.be_date


def parse_import_rows(rows: list[ParsedRow], column_mapping: dict[str, str]) -> list[ParsedImportTransaction]:
    parsed: list[ParsedImportTransaction] = []
    for row in rows:
        mapped = {target: row.values.get(header) for header, target in column_mapping.items()}

        be_number = to_text(mapped.get("be_number"))
        item_description = to_text(mapped.get("item_description"))
        hs_code = to_text(mapped.get("hs_code"))
        declared_quantity = to_decimal(mapped.get("declared_quantity"))

        if be_number is None or item_description is None or hs_code is None or declared_quantity is None:
            continue  # not a usable transaction row (title/subtotal/blank row)

        parsed.append(
            ParsedImportTransaction(
                row_number=row.row_number,
                be_number=be_number,
                be_date=to_date(mapped.get("be_date")),
                import_date=to_date(mapped.get("import_date")),
                lc_number=to_text(mapped.get("lc_number")),
                invoice_number=to_text(mapped.get("invoice_number")),
                item_description=item_description,
                hs_code=hs_code,
                declared_quantity=declared_quantity,
                declared_unit=to_text(mapped.get("declared_unit")) or "",
                original_currency=to_text(mapped.get("original_currency")),
                original_currency_value=to_decimal(mapped.get("original_currency_value")),
                raw_values=dict(row.values),
            )
        )
    return parsed


def filter_to_audit_period(
    transactions: list[ParsedImportTransaction], period_start: date, period_end: date
) -> tuple[list[ParsedImportTransaction], list[ParsedImportTransaction]]:
    """Returns (in_period, excluded). A transaction with no usable date at all is
    excluded rather than guessed into the period — it's returned in `excluded` so the
    caller can still surface it as a data-quality issue instead of silently dropping it."""
    in_period: list[ParsedImportTransaction] = []
    excluded: list[ParsedImportTransaction] = []
    for txn in transactions:
        txn_date = txn.transaction_date
        if txn_date is not None and period_start <= txn_date <= period_end:
            in_period.append(txn)
        else:
            excluded.append(txn)
    return in_period, excluded
