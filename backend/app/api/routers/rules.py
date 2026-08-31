from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.core.permissions import Permission
from app.models.entitlement import EntitlementGroup, EntitlementItem
from app.models.enums import Classification, ExcessStatus, MatchStatus
from app.models.import_transaction import ImportTransaction
from app.models.user import User
from app.schemas.exceptions import ClassifyResult, DetectExcessResult, ExceptionDashboardOut
from app.services import audit_trail
from app.services.classification_engine import classify
from app.services.exception_queries import compute_exceptions
from app.services.excess_engine import ExcessLineInput, compute_chronological_excess

router = APIRouter(prefix="/api/audits/{audit_id}", tags=["audit-rules"])

# A classification with this confidence was written by a human override
# (see imports.override_classification) — bulk reclassification must never clobber it.
MANUAL_OVERRIDE_CONFIDENCE = 1.0

# Below this the transaction is UNKNOWN either way, so treating anything under it as
# "not manual" is safe: a real manual override is always recorded at exactly 1.0.
_MANUAL_EPSILON = 1e-9


@router.post("/classify", response_model=ClassifyResult)
def classify_imports(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> ClassifyResult:
    """M05, re-runnable: reclassifies every transaction whose classification wasn't a
    manual auditor override (spec section 3: AI suggestions must not silently
    overwrite a human decision)."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)

    entitlement_hs_codes = {
        item.hs_code
        for item in (
            db.query(EntitlementItem)
            .join(EntitlementGroup, EntitlementItem.group_id == EntitlementGroup.id)
            .filter(EntitlementGroup.audit_id == audit_id)
            .all()
        )
        if item.hs_code
    }

    transactions = db.query(ImportTransaction).filter(ImportTransaction.audit_id == audit_id).all()
    reclassified = 0
    skipped = 0
    breakdown: Counter[str] = Counter()
    for txn in transactions:
        if abs(float(txn.classification_confidence) - MANUAL_OVERRIDE_CONFIDENCE) < _MANUAL_EPSILON:
            skipped += 1
            breakdown[txn.classification] += 1
            continue
        classification, confidence = classify(txn.item_description, txn.hs_code, entitlement_hs_codes)
        txn.classification = classification
        txn.classification_confidence = confidence
        breakdown[classification] += 1
        reclassified += 1

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="import_transactions",
        entity_id=audit_id,
        action="classify.bulk",
        new_value={"reclassified": reclassified, "skipped_manual": skipped, "breakdown": dict(breakdown)},
        audit_id=audit_id,
    )
    db.commit()
    return ClassifyResult(reclassified_count=reclassified, skipped_manual_override_count=skipped, classification_breakdown=dict(breakdown))


@router.post("/detect-excess", response_model=DetectExcessResult)
def detect_excess(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> DetectExcessResult:
    """M08 + spec section 13's unauthorized-import check, combined into one pass:

    1. Any RAW_MATERIAL transaction whose match was never approved is NON_ENTITLED.
    2. Every APPROVED, converted transaction is run through the chronological excess
       engine per entitlement item.
    """
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)

    raw_material_txns = (
        db.query(ImportTransaction)
        .filter(ImportTransaction.audit_id == audit_id, ImportTransaction.classification == Classification.RAW_MATERIAL)
        .all()
    )

    non_entitled_marked = 0
    for txn in raw_material_txns:
        if txn.match_status != MatchStatus.APPROVED:
            txn.non_entitled = True
            non_entitled_marked += 1
        else:
            txn.non_entitled = False

    approved_txns = [t for t in raw_material_txns if t.match_status == MatchStatus.APPROVED and t.entitlement_item_id]
    by_item: dict[str, list[ImportTransaction]] = {}
    for txn in approved_txns:
        by_item.setdefault(txn.entitlement_item_id, []).append(txn)

    within = partial = full = skipped_unconverted = 0
    for entitlement_item_id, txns in by_item.items():
        item = db.get(EntitlementItem, entitlement_item_id)
        if item is None:
            continue
        convertible = [t for t in txns if t.entitlement_quantity is not None]
        skipped_unconverted += len(txns) - len(convertible)
        if not convertible:
            continue

        lines = [
            ExcessLineInput(transaction_id=t.id, be_date=t.be_date, be_number=t.be_number, entitlement_quantity=t.entitlement_quantity)
            for t in convertible
        ]
        results = compute_chronological_excess(lines, item.total_entitlement_qty)
        results_by_id = {r.transaction_id: r for r in results}
        for txn in convertible:
            result = results_by_id[txn.id]
            txn.excess_status = result.excess_status
            txn.allowed_quantity = result.allowed_quantity
            txn.excess_quantity = result.excess_quantity
            txn.cumulative_quantity_after = result.cumulative_quantity_after
            if result.excess_status == ExcessStatus.WITHIN_ENTITLEMENT:
                within += 1
            elif result.excess_status == ExcessStatus.PARTIAL_EXCESS:
                partial += 1
            elif result.excess_status == ExcessStatus.FULL_EXCESS:
                full += 1

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="import_transactions",
        entity_id=audit_id,
        action="excess.detect",
        new_value={
            "non_entitled_marked": non_entitled_marked,
            "entitlement_items_processed": len(by_item),
            "within_entitlement": within,
            "partial_excess": partial,
            "full_excess": full,
            "skipped_unconverted": skipped_unconverted,
        },
        audit_id=audit_id,
    )
    db.commit()

    return DetectExcessResult(
        non_entitled_marked_count=non_entitled_marked,
        entitlement_items_processed=len(by_item),
        within_entitlement_count=within,
        partial_excess_count=partial,
        full_excess_count=full,
        skipped_unconverted_count=skipped_unconverted,
    )


@router.get("/exceptions", response_model=ExceptionDashboardOut)
def exception_dashboard(
    audit_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> ExceptionDashboardOut:
    """OUTPUT 04 preview (JSON, for the frontend dashboard — the Excel export of the
    same data is generated by the reporting engine)."""
    get_audit_or_404(db, audit_id)
    data = compute_exceptions(db, audit_id)

    return ExceptionDashboardOut(
        non_entitled_count=len(data.non_entitled),
        review_required_match_count=len(data.review_required),
        unknown_classification_count=len(data.unknown_classification),
        partial_excess_count=len([t for t in data.excess if t.excess_status == ExcessStatus.PARTIAL_EXCESS]),
        full_excess_count=len([t for t in data.excess if t.excess_status == ExcessStatus.FULL_EXCESS]),
        conversion_incomplete_count=len(data.conversion_incomplete),
        non_entitled_transactions=data.non_entitled,
        review_required_transactions=data.review_required,
        excess_transactions=data.excess,
        conversion_incomplete_transactions=data.conversion_incomplete,
    )
