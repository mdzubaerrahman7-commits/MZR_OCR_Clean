"""Shared query logic for the exception dashboard (spec OUTPUT 04), used by both the
JSON dashboard endpoint (rules.py) and the Excel export (reports.py) so the two never
drift apart. Takes a Session (this is a query helper, not a pure engine) but never
imports FastAPI."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.enums import Classification, ExcessStatus, MatchStatus
from app.models.import_transaction import ImportTransaction


@dataclass
class ExceptionData:
    non_entitled: list[ImportTransaction]
    review_required: list[ImportTransaction]
    unknown_classification: list[ImportTransaction]
    excess: list[ImportTransaction]
    conversion_incomplete: list[ImportTransaction]


def compute_exceptions(db: Session, audit_id: str) -> ExceptionData:
    all_txns = db.query(ImportTransaction).filter(ImportTransaction.audit_id == audit_id).all()

    non_entitled = [t for t in all_txns if t.non_entitled]
    review_required = [t for t in all_txns if t.match_status == MatchStatus.REVIEW_REQUIRED]
    unknown_classification = [t for t in all_txns if t.classification == Classification.UNKNOWN]
    excess = [t for t in all_txns if t.excess_status in (ExcessStatus.PARTIAL_EXCESS, ExcessStatus.FULL_EXCESS)]
    conversion_incomplete = [
        t
        for t in all_txns
        if t.classification == Classification.RAW_MATERIAL
        and t.match_status == MatchStatus.APPROVED
        and (t.entitlement_quantity is None or t.kg_quantity is None or t.usd_value is None)
    ]

    return ExceptionData(
        non_entitled=non_entitled,
        review_required=review_required,
        unknown_classification=unknown_classification,
        excess=excess,
        conversion_incomplete=conversion_incomplete,
    )
