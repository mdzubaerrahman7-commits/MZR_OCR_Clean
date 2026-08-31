"""M10 — Findings Register generation (spec OUTPUT 07).

A pure function decides *what findings should exist* from the current state of the
transactions; the router (generate-findings) is responsible for diffing that against
what's already stored and upserting without disturbing an existing finding's
review_status/reviewed_by — regenerating findings after new evidence must never
silently reset a reviewer's approval (spec section 19: every decision needs an
audit trail, section 3: never silently modify).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import ExcessStatus, FindingIssueType
from app.services.duty_engine import prorated_demand


@dataclass(frozen=True)
class FindingSourceTransaction:
    transaction_id: str
    be_number: str
    material_name: str
    hs_code: str
    declared_quantity: Decimal
    declared_unit: str
    usd_value: Decimal | None
    non_entitled: bool
    excess_status: str
    excess_quantity: Decimal | None
    classification: str
    entitlement_item_id: str | None


@dataclass(frozen=True)
class FindingDraft:
    issue_type: str
    evidence: str
    bill_of_entry_id: str | None
    entitlement_item_id: str | None
    material_name: str
    quantity: Decimal
    unit: str
    value: Decimal | None
    demand_amount: Decimal | None


FindingKey = tuple[str, str]  # (transaction_id, issue_type)


def build_finding_drafts(
    transactions: list[FindingSourceTransaction],
    bill_of_entry_id_by_number: dict[str, str],
    total_duty_by_be_number: dict[str, Decimal],
) -> dict[FindingKey, FindingDraft]:
    drafts: dict[FindingKey, FindingDraft] = {}

    for txn in transactions:
        boe_id = bill_of_entry_id_by_number.get(txn.be_number)
        total_duty = total_duty_by_be_number.get(txn.be_number)

        if txn.non_entitled:
            demand = prorated_demand(total_duty, txn.declared_quantity, txn.declared_quantity)
            drafts[(txn.transaction_id, FindingIssueType.NON_ENTITLED)] = FindingDraft(
                issue_type=FindingIssueType.NON_ENTITLED,
                evidence=f"B/E {txn.be_number}: HS {txn.hs_code} ({txn.material_name}) has no approved entitlement mapping.",
                bill_of_entry_id=boe_id,
                entitlement_item_id=txn.entitlement_item_id,
                material_name=txn.material_name,
                quantity=txn.declared_quantity,
                unit=txn.declared_unit,
                value=txn.usd_value,
                demand_amount=demand,
            )

        if txn.excess_status in (ExcessStatus.PARTIAL_EXCESS, ExcessStatus.FULL_EXCESS) and txn.excess_quantity:
            issue_type = (
                FindingIssueType.EXCESS_PARTIAL if txn.excess_status == ExcessStatus.PARTIAL_EXCESS else FindingIssueType.EXCESS_FULL
            )
            demand = prorated_demand(total_duty, txn.excess_quantity, txn.declared_quantity)
            drafts[(txn.transaction_id, issue_type)] = FindingDraft(
                issue_type=issue_type,
                evidence=(
                    f"B/E {txn.be_number}: {txn.excess_quantity} {txn.declared_unit} of {txn.material_name} "
                    f"(HS {txn.hs_code}) exceeds approved entitlement ({txn.excess_status})."
                ),
                bill_of_entry_id=boe_id,
                entitlement_item_id=txn.entitlement_item_id,
                material_name=txn.material_name,
                quantity=txn.excess_quantity,
                unit=txn.declared_unit,
                value=txn.usd_value,
                demand_amount=demand,
            )

        if txn.classification == "unknown":
            drafts[(txn.transaction_id, FindingIssueType.CLASSIFICATION_REVIEW)] = FindingDraft(
                issue_type=FindingIssueType.CLASSIFICATION_REVIEW,
                evidence=f"B/E {txn.be_number}: '{txn.material_name}' (HS {txn.hs_code}) could not be confidently classified.",
                bill_of_entry_id=boe_id,
                entitlement_item_id=None,
                material_name=txn.material_name,
                quantity=txn.declared_quantity,
                unit=txn.declared_unit,
                value=txn.usd_value,
                demand_amount=None,
            )

    return drafts
