from decimal import Decimal

from app.models.enums import ExcessStatus, FindingIssueType
from app.services.finding_engine import FindingSourceTransaction, build_finding_drafts


def _txn(**overrides) -> FindingSourceTransaction:
    base = dict(
        transaction_id="t1",
        be_number="C-0001",
        material_name="Polypropylene Resin",
        hs_code="3902.10.00",
        declared_quantity=Decimal("1000"),
        declared_unit="KG",
        usd_value=Decimal("5000"),
        non_entitled=False,
        excess_status=ExcessStatus.NOT_APPLICABLE,
        excess_quantity=None,
        classification="raw_material",
        entitlement_item_id="e1",
    )
    base.update(overrides)
    return FindingSourceTransaction(**base)


def test_non_entitled_transaction_creates_finding_with_full_quantity_demand() -> None:
    txn = _txn(non_entitled=True, entitlement_item_id=None)
    drafts = build_finding_drafts([txn], {"C-0001": "boe1"}, {"C-0001": Decimal("1000.00")})
    key = ("t1", FindingIssueType.NON_ENTITLED)
    assert key in drafts
    assert drafts[key].demand_amount == Decimal("1000.00")
    assert drafts[key].quantity == Decimal("1000")


def test_partial_excess_finding_uses_excess_quantity_only() -> None:
    txn = _txn(excess_status=ExcessStatus.PARTIAL_EXCESS, excess_quantity=Decimal("500"))
    drafts = build_finding_drafts([txn], {"C-0001": "boe1"}, {"C-0001": Decimal("1000.00")})
    key = ("t1", FindingIssueType.EXCESS_PARTIAL)
    assert key in drafts
    assert drafts[key].quantity == Decimal("500")
    assert drafts[key].demand_amount == Decimal("500.00")  # half the declared quantity is excess


def test_unknown_classification_creates_review_finding_with_no_demand() -> None:
    txn = _txn(classification="unknown")
    drafts = build_finding_drafts([txn], {}, {})
    key = ("t1", FindingIssueType.CLASSIFICATION_REVIEW)
    assert key in drafts
    assert drafts[key].demand_amount is None


def test_clean_within_entitlement_transaction_produces_no_findings() -> None:
    txn = _txn(excess_status=ExcessStatus.WITHIN_ENTITLEMENT)
    drafts = build_finding_drafts([txn], {"C-0001": "boe1"}, {"C-0001": Decimal("1000.00")})
    assert drafts == {}


def test_missing_duty_evidence_yields_none_demand_not_zero() -> None:
    txn = _txn(non_entitled=True)
    drafts = build_finding_drafts([txn], {"C-0001": "boe1"}, {})
    key = ("t1", FindingIssueType.NON_ENTITLED)
    assert drafts[key].demand_amount is None


def test_transaction_can_produce_multiple_findings() -> None:
    txn = _txn(non_entitled=True, excess_status=ExcessStatus.FULL_EXCESS, excess_quantity=Decimal("1000"))
    drafts = build_finding_drafts([txn], {"C-0001": "boe1"}, {"C-0001": Decimal("1000.00")})
    assert ("t1", FindingIssueType.NON_ENTITLED) in drafts
    assert ("t1", FindingIssueType.EXCESS_FULL) in drafts
