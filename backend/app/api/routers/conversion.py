from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.core.permissions import Permission
from app.models.bill_of_entry import BillOfEntry
from app.models.entitlement import EntitlementItem
from app.models.enums import MatchStatus
from app.models.import_transaction import ImportTransaction
from app.models.user import User
from app.schemas.matching import ConversionBulkResult
from app.services import audit_trail
from app.services.conversion_engine import BillOfEntryEvidence, convert_transaction

router = APIRouter(prefix="/api/audits/{audit_id}/calculate-conversions", tags=["conversion"])


@router.post("", response_model=ConversionBulkResult)
def calculate_conversions(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> ConversionBulkResult:
    """M07: convert every APPROVED-match transaction using its matched entitlement
    item's unit and the evidence recorded against its Bill of Entry. Re-runnable —
    always recomputed from current evidence, never accumulated."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)

    transactions = (
        db.query(ImportTransaction)
        .filter(ImportTransaction.audit_id == audit_id, ImportTransaction.match_status == MatchStatus.APPROVED)
        .all()
    )

    boe_by_number = {
        boe.be_number: boe for boe in db.query(BillOfEntry).filter(BillOfEntry.audit_id == audit_id).all()
    }

    fully_converted_count = 0
    for txn in transactions:
        entitlement_item = db.get(EntitlementItem, txn.entitlement_item_id) if txn.entitlement_item_id else None
        boe = boe_by_number.get(txn.be_number)
        evidence = (
            BillOfEntryEvidence(
                exchange_rate=boe.exchange_rate,
                exchange_rate_evidence=boe.exchange_rate_evidence,
                kg_conversion_factor=boe.kg_conversion_factor,
                kg_conversion_evidence=boe.kg_conversion_evidence,
                entitlement_conversion_factor=boe.entitlement_conversion_factor,
                entitlement_conversion_evidence=boe.entitlement_conversion_evidence,
            )
            if boe
            else None
        )

        result = convert_transaction(
            declared_quantity=txn.declared_quantity,
            declared_unit=txn.declared_unit,
            entitlement_unit=entitlement_item.entitlement_unit if entitlement_item else None,
            original_currency=txn.original_currency,
            original_currency_value=txn.original_currency_value,
            be_evidence=evidence,
        )

        txn.entitlement_unit = entitlement_item.entitlement_unit if entitlement_item else None
        txn.entitlement_quantity = result.entitlement_quantity
        txn.kg_quantity = result.kg_quantity
        txn.usd_value = result.usd_value
        txn.assessable_value = boe.assessable_value if boe and boe.assessable_value is not None else result.usd_value
        txn.conversion_evidence = " | ".join(result.evidence_notes) if result.evidence_notes else None
        if result.fully_converted:
            fully_converted_count += 1

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="import_transactions",
        entity_id=audit_id,
        action="conversion.calculate",
        new_value={
            "processed_count": len(transactions),
            "fully_converted_count": fully_converted_count,
            "incomplete_count": len(transactions) - fully_converted_count,
        },
        audit_id=audit_id,
    )
    db.commit()

    return ConversionBulkResult(
        processed_count=len(transactions),
        fully_converted_count=fully_converted_count,
        incomplete_count=len(transactions) - fully_converted_count,
    )
