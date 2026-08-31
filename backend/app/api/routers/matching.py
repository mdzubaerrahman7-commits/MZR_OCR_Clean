from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.api.routers.imports import get_import_transaction_or_404
from app.core.permissions import Permission
from app.models.entitlement import EntitlementGroup, EntitlementItem
from app.models.enums import Classification, MatchStatus
from app.models.import_transaction import ImportTransaction
from app.models.user import User
from app.schemas.entitlement import EntitlementItemOut
from app.schemas.import_transaction import ImportTransactionOut
from app.schemas.matching import MatchBulkSuggestResult, MatchConfirmRequest
from app.services import audit_trail
from app.services.matching_engine import EntitlementCandidate, suggest_match

audit_router = APIRouter(prefix="/api/audits/{audit_id}", tags=["matching"])

VALID_DECISIONS = {MatchStatus.APPROVED, MatchStatus.REJECTED, MatchStatus.REVIEW_REQUIRED}


def _candidates(db: Session, audit_id: str) -> list[EntitlementCandidate]:
    items = (
        db.query(EntitlementItem)
        .join(EntitlementGroup, EntitlementItem.group_id == EntitlementGroup.id)
        .filter(EntitlementGroup.audit_id == audit_id, EntitlementItem.active.is_(True))
        .all()
    )
    return [EntitlementCandidate(entitlement_item_id=i.id, hs_code=i.hs_code, material_name=i.material_name) for i in items]


@audit_router.post("/match-entitlements", response_model=MatchBulkSuggestResult)
def match_entitlements(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> MatchBulkSuggestResult:
    """M06 bulk suggestion pass. Only ever writes MatchStatus.SUGGESTED (or
    REVIEW_REQUIRED when no candidate exists) — auditor confirmation is a separate,
    explicit step (see confirm_match below)."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)

    candidates = _candidates(db, audit_id)
    pending = (
        db.query(ImportTransaction)
        .filter(
            ImportTransaction.audit_id == audit_id,
            ImportTransaction.classification == Classification.RAW_MATERIAL,
            ImportTransaction.match_status == MatchStatus.UNMATCHED,
        )
        .all()
    )

    suggested_count = 0
    no_suggestion_count = 0
    for txn in pending:
        suggestion = suggest_match(txn.hs_code, txn.item_description, candidates)
        if suggestion is None:
            txn.match_status = MatchStatus.REVIEW_REQUIRED
            txn.match_evidence = "No entitlement candidate found by HS code or material name similarity."
            no_suggestion_count += 1
        else:
            txn.match_status = MatchStatus.SUGGESTED
            txn.entitlement_item_id = suggestion.entitlement_item_id
            txn.match_confidence = suggestion.confidence
            txn.match_evidence = suggestion.evidence
            suggested_count += 1

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="import_transactions",
        entity_id=audit_id,
        action="matching.bulk_suggest",
        new_value={"candidates_considered": len(pending), "suggested": suggested_count, "no_suggestion": no_suggestion_count},
        audit_id=audit_id,
    )
    db.commit()
    return MatchBulkSuggestResult(
        candidates_considered=len(pending), suggested_count=suggested_count, no_suggestion_count=no_suggestion_count
    )


@audit_router.get("/imports/{transaction_id}/match-candidates", response_model=list[EntitlementItemOut])
def list_match_candidates(
    audit_id: str,
    transaction_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[EntitlementItem]:
    """For the manual confirmation UI: every active entitlement item an auditor could
    pick instead of (or to confirm) the engine's suggestion."""
    get_audit_or_404(db, audit_id)
    get_import_transaction_or_404(db, audit_id, transaction_id)
    return (
        db.query(EntitlementItem)
        .join(EntitlementGroup, EntitlementItem.group_id == EntitlementGroup.id)
        .filter(EntitlementGroup.audit_id == audit_id, EntitlementItem.active.is_(True))
        .order_by(EntitlementGroup.sequence_no, EntitlementItem.sequence_no)
        .all()
    )


@audit_router.post("/imports/{transaction_id}/match/confirm", response_model=ImportTransactionOut)
def confirm_match(
    audit_id: str,
    transaction_id: str,
    payload: MatchConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.APPROVE_DECISIONS)),
) -> ImportTransaction:
    """The only place a match can become APPROVED/REJECTED/REVIEW_REQUIRED (spec
    section 10 step 4). An auditor may confirm the engine's suggestion as-is or
    override it with a different entitlement_item_id — either way the decision and
    its reason are captured in the audit trail."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    txn = get_import_transaction_or_404(db, audit_id, transaction_id)

    if payload.decision not in {d.value for d in VALID_DECISIONS}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="decision must be approved, rejected or review_required")

    target_entitlement_item_id = payload.entitlement_item_id or txn.entitlement_item_id
    if payload.decision == MatchStatus.APPROVED and not target_entitlement_item_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Approving a match requires an entitlement_item_id")

    old_value = {"match_status": txn.match_status, "entitlement_item_id": txn.entitlement_item_id}
    txn.match_status = payload.decision
    if payload.decision == MatchStatus.APPROVED:
        txn.entitlement_item_id = target_entitlement_item_id
    elif payload.decision == MatchStatus.REJECTED:
        txn.entitlement_item_id = None

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="import_transaction",
        entity_id=txn.id,
        action="match.confirm",
        old_value=old_value,
        new_value={"match_status": txn.match_status, "entitlement_item_id": txn.entitlement_item_id},
        audit_id=audit_id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(txn)
    return txn
