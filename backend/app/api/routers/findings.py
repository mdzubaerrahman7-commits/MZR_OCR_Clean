from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.core.permissions import Permission
from app.db.base import utcnow
from app.models.bill_of_entry import BillOfEntry
from app.models.finding import Finding
from app.models.import_transaction import ImportTransaction
from app.models.user import User
from app.schemas.finding import FindingOut, FindingReviewRequest, GenerateFindingsResult
from app.services import audit_trail
from app.services.duty_engine import sum_duty_components
from app.services.finding_engine import FindingSourceTransaction, build_finding_drafts

router = APIRouter(prefix="/api/audits/{audit_id}", tags=["findings"])

VALID_REVIEW_DECISIONS = {"approved", "rejected", "under_review"}


@router.post("/generate-findings", response_model=GenerateFindingsResult)
def generate_findings(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> GenerateFindingsResult:
    """M09 + OUTPUT 07. Idempotent: re-running this after new evidence updates each
    finding's figures but never resets an existing review_status/reviewed_by — a
    finding that no longer applies (e.g. the transaction was re-matched and is no
    longer non-entitled) is removed instead of left stale."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)

    transactions = db.query(ImportTransaction).filter(ImportTransaction.audit_id == audit_id).all()
    bill_of_entries = db.query(BillOfEntry).filter(BillOfEntry.audit_id == audit_id).all()

    boe_id_by_number = {boe.be_number: boe.id for boe in bill_of_entries}
    total_duty_by_be_number = {
        boe.be_number: sum_duty_components([dc.calculated_amount for dc in boe.duty_components]) for boe in bill_of_entries
    }

    source_transactions = [
        FindingSourceTransaction(
            transaction_id=t.id,
            be_number=t.be_number,
            material_name=t.item_description,
            hs_code=t.hs_code,
            declared_quantity=t.declared_quantity,
            declared_unit=t.declared_unit,
            usd_value=t.usd_value,
            non_entitled=t.non_entitled,
            excess_status=t.excess_status,
            excess_quantity=t.excess_quantity,
            classification=t.classification,
            entitlement_item_id=t.entitlement_item_id,
        )
        for t in transactions
    ]
    desired = build_finding_drafts(source_transactions, boe_id_by_number, total_duty_by_be_number)

    existing = db.query(Finding).filter(Finding.audit_id == audit_id).all()
    existing_by_key = {(f.import_transaction_id, f.issue_type): f for f in existing}

    created = updated = removed = 0

    for key, finding in list(existing_by_key.items()):
        if key not in desired:
            db.delete(finding)
            removed += 1
            del existing_by_key[key]

    for key, draft in desired.items():
        transaction_id, issue_type = key
        if key in existing_by_key:
            finding = existing_by_key[key]
            finding.evidence = draft.evidence
            finding.bill_of_entry_id = draft.bill_of_entry_id
            finding.entitlement_item_id = draft.entitlement_item_id
            finding.material_name = draft.material_name
            finding.quantity = draft.quantity
            finding.unit = draft.unit
            finding.value = draft.value
            finding.demand_amount = draft.demand_amount
            updated += 1
        else:
            db.add(
                Finding(
                    audit_id=audit_id,
                    finding_code="PENDING",
                    issue_type=draft.issue_type,
                    evidence=draft.evidence,
                    bill_of_entry_id=draft.bill_of_entry_id,
                    import_transaction_id=transaction_id,
                    entitlement_item_id=draft.entitlement_item_id,
                    material_name=draft.material_name,
                    quantity=draft.quantity,
                    unit=draft.unit,
                    value=draft.value,
                    demand_amount=draft.demand_amount,
                )
            )
            created += 1

    db.flush()

    # Deterministic, stable renumbering after every regeneration.
    all_findings = (
        db.query(Finding)
        .filter(Finding.audit_id == audit_id)
        .order_by(Finding.issue_type, Finding.material_name, Finding.import_transaction_id)
        .all()
    )
    for idx, finding in enumerate(all_findings, start=1):
        finding.finding_code = f"F-{idx:04d}"

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="findings",
        entity_id=audit_id,
        action="findings.generate",
        new_value={"created": created, "updated": updated, "removed": removed, "total": len(all_findings)},
        audit_id=audit_id,
    )
    db.commit()

    return GenerateFindingsResult(created_count=created, updated_count=updated, removed_count=removed, total_findings=len(all_findings))


@router.get("/findings", response_model=list[FindingOut])
def list_findings(
    audit_id: str,
    issue_type: str | None = None,
    review_status: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[Finding]:
    get_audit_or_404(db, audit_id)
    query = db.query(Finding).filter(Finding.audit_id == audit_id)
    if issue_type:
        query = query.filter(Finding.issue_type == issue_type)
    if review_status:
        query = query.filter(Finding.review_status == review_status)
    return query.order_by(Finding.finding_code).all()


@router.patch("/findings/{finding_id}/review", response_model=FindingOut)
def review_finding(
    audit_id: str,
    finding_id: str,
    payload: FindingReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.APPROVE_FINDINGS)),
) -> Finding:
    """Spec M10/section 20: Reviewer/Supervisor approves or rejects a finding.
    Every decision is logged with old/new status, reviewer identity and reason."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    finding = db.get(Finding, finding_id)
    if finding is None or finding.audit_id != audit_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    if payload.decision not in VALID_REVIEW_DECISIONS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="decision must be approved, rejected or under_review")

    old_value = {"review_status": finding.review_status}
    finding.review_status = payload.decision
    finding.reviewed_by = current_user.id
    finding.reviewed_at = utcnow()
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="finding",
        entity_id=finding.id,
        action="finding.review",
        old_value=old_value,
        new_value={"review_status": finding.review_status},
        audit_id=audit_id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(finding)
    return finding
