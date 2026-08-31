from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.mapping_helpers import get_confirmed_mapping
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.api.routers.documents import get_document_or_404
from app.core.permissions import Permission
from app.models.entitlement import EntitlementGroup, EntitlementItem
from app.models.enums import Classification
from app.models.import_transaction import ImportTransaction
from app.models.user import User
from app.schemas.import_transaction import (
    ClassificationOverrideRequest,
    ImportTransactionOut,
    ParseImportMisRequest,
    ParseImportMisResult,
)
from app.services import audit_trail, excel_intelligence, storage
from app.services.classification_engine import classify
from app.services.import_engine import filter_to_audit_period, parse_import_rows
from app.services.numeric import json_safe_row

router = APIRouter(prefix="/api/audits/{audit_id}/imports", tags=["imports"])


@router.post("/parse", response_model=ParseImportMisResult)
def parse_import_mis(
    audit_id: str,
    payload: ParseImportMisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> ParseImportMisResult:
    """M05 + audit-period filter (spec section 2). Re-running this replaces the
    previously-parsed transactions for this audit — the source document/rows behind
    it are untouched; only the derived transaction set is regenerated, same as the
    entitlement engine."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    document = get_document_or_404(db, audit_id, payload.source_document_id)

    column_mapping = get_confirmed_mapping(db, document.id, payload.sheet_name)
    backend = storage.get_storage_backend()
    content = backend.read(document.storage_key)
    detection = excel_intelligence.detect_header_row(content, payload.sheet_name)
    rows = excel_intelligence.read_rows(content, payload.sheet_name, detection.header_row_index, detection.headers)
    parsed = parse_import_rows(rows, column_mapping)
    in_period, excluded = filter_to_audit_period(parsed, audit.audit_period_start, audit.audit_period_end)

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

    existing = db.query(ImportTransaction).filter(ImportTransaction.audit_id == audit_id).all()
    old_count = len(existing)
    for txn in existing:
        db.delete(txn)
    db.flush()

    breakdown: Counter[str] = Counter()
    for parsed_txn in in_period:
        classification, confidence = classify(parsed_txn.item_description, parsed_txn.hs_code, entitlement_hs_codes)
        breakdown[classification] += 1
        db.add(
            ImportTransaction(
                audit_id=audit_id,
                source_document_id=document.id,
                source_row_number=parsed_txn.row_number,
                raw_payload=json_safe_row(parsed_txn.raw_values),
                be_number=parsed_txn.be_number,
                be_date=parsed_txn.be_date or parsed_txn.import_date,
                import_date=parsed_txn.import_date,
                lc_number=parsed_txn.lc_number,
                invoice_number=parsed_txn.invoice_number,
                item_description=parsed_txn.item_description,
                hs_code=parsed_txn.hs_code,
                declared_quantity=parsed_txn.declared_quantity,
                declared_unit=parsed_txn.declared_unit,
                original_currency=parsed_txn.original_currency,
                original_currency_value=parsed_txn.original_currency_value,
                classification=classification,
                classification_confidence=confidence,
            )
        )

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="import_transactions",
        entity_id=audit_id,
        action="imports.parse",
        old_value={"transaction_count": old_count},
        new_value={
            "parsed_count": len(parsed),
            "in_period_count": len(in_period),
            "excluded_out_of_period_count": len(excluded),
            "classification_breakdown": dict(breakdown),
        },
        audit_id=audit_id,
    )
    db.commit()

    return ParseImportMisResult(
        parsed_count=len(parsed),
        in_period_count=len(in_period),
        excluded_out_of_period_count=len(excluded),
        classification_breakdown=dict(breakdown),
    )


@router.get("", response_model=list[ImportTransactionOut])
def list_imports(
    audit_id: str,
    classification: Classification | None = None,
    review_required: bool = False,
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[ImportTransaction]:
    get_audit_or_404(db, audit_id)
    query = db.query(ImportTransaction).filter(ImportTransaction.audit_id == audit_id)
    if classification:
        query = query.filter(ImportTransaction.classification == classification)
    if review_required:
        query = query.filter(
            (ImportTransaction.classification == Classification.UNKNOWN)
            | (ImportTransaction.classification_confidence < 0.5)
        )
    return query.order_by(ImportTransaction.be_date, ImportTransaction.source_row_number).offset(offset).limit(limit).all()


def get_import_transaction_or_404(db: Session, audit_id: str, transaction_id: str) -> ImportTransaction:
    txn = db.get(ImportTransaction, transaction_id)
    if txn is None or txn.audit_id != audit_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import transaction not found")
    return txn


@router.patch("/{transaction_id}/classification", response_model=ImportTransactionOut)
def override_classification(
    audit_id: str,
    transaction_id: str,
    payload: ClassificationOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REVIEW_EXCEPTIONS)),
) -> ImportTransaction:
    """Mandatory auditor review path for Unknown/low-confidence rows (spec section 15).
    A manual override always carries a reason and is captured in the audit trail —
    it is never a silent correction of the engine's output."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    txn = get_import_transaction_or_404(db, audit_id, transaction_id)

    if payload.classification not in {c.value for c in Classification}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid classification value")

    old_value = {"classification": txn.classification, "classification_confidence": float(txn.classification_confidence)}
    txn.classification = payload.classification
    txn.classification_confidence = 1.0  # a manual auditor decision is by definition fully confident
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="import_transaction",
        entity_id=txn.id,
        action="classification.override",
        old_value=old_value,
        new_value={"classification": txn.classification},
        audit_id=audit_id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(txn)
    return txn
