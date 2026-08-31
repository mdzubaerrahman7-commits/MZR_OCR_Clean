from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.core.permissions import Permission
from app.models.bill_of_entry import BillOfEntry, DutyComponent
from app.models.user import User
from app.schemas.bill_of_entry import BillOfEntryOut, BillOfEntryUpsert, DutyComponentIn, DutyComponentOut
from app.services import audit_trail

router = APIRouter(prefix="/api/audits/{audit_id}/bill-of-entries", tags=["bill-of-entries"])


@router.post("", response_model=BillOfEntryOut, status_code=status.HTTP_201_CREATED)
def upsert_bill_of_entry(
    audit_id: str,
    payload: BillOfEntryUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> BillOfEntry:
    """Records the B/E-level conversion/exchange-rate/assessable-value evidence that
    M07 requires before it will convert a transaction (spec section 9)."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)

    existing = db.query(BillOfEntry).filter(BillOfEntry.audit_id == audit_id, BillOfEntry.be_number == payload.be_number).first()
    old_value = None
    if existing:
        old_value = {
            "exchange_rate": str(existing.exchange_rate) if existing.exchange_rate is not None else None,
            "kg_conversion_factor": str(existing.kg_conversion_factor) if existing.kg_conversion_factor is not None else None,
            "entitlement_conversion_factor": (
                str(existing.entitlement_conversion_factor) if existing.entitlement_conversion_factor is not None else None
            ),
            "assessable_value": str(existing.assessable_value) if existing.assessable_value is not None else None,
        }
        for key, value in payload.model_dump(exclude={"be_number"}).items():
            setattr(existing, key, value)
        bill_of_entry = existing
    else:
        bill_of_entry = BillOfEntry(audit_id=audit_id, **payload.model_dump())
        db.add(bill_of_entry)

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="bill_of_entry",
        entity_id=bill_of_entry.id,
        action="bill_of_entry.upsert",
        old_value=old_value,
        new_value=payload.model_dump(mode="json"),
        audit_id=audit_id,
    )
    db.commit()
    db.refresh(bill_of_entry)
    return bill_of_entry


@router.get("", response_model=list[BillOfEntryOut])
def list_bill_of_entries(
    audit_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[BillOfEntry]:
    get_audit_or_404(db, audit_id)
    return db.query(BillOfEntry).filter(BillOfEntry.audit_id == audit_id).order_by(BillOfEntry.be_date, BillOfEntry.be_number).all()


def get_bill_of_entry_or_404(db: Session, audit_id: str, be_id: str) -> BillOfEntry:
    boe = db.get(BillOfEntry, be_id)
    if boe is None or boe.audit_id != audit_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill of Entry not found")
    return boe


@router.post("/{be_id}/duty-components", response_model=DutyComponentOut, status_code=status.HTTP_201_CREATED)
def add_duty_component(
    audit_id: str,
    be_id: str,
    payload: DutyComponentIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> DutyComponent:
    """Spec section 9: duty_components (CD/RD/SD/VAT/AIT/AT/...) belong to a Bill of
    Entry. calculated_amount = base_amount * rate, computed here (Decimal, never
    float) rather than trusted from the source to keep it reproducible."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    boe = get_bill_of_entry_or_404(db, audit_id, be_id)

    component = DutyComponent(
        bill_of_entry_id=boe.id,
        component_code=payload.component_code,
        rate=payload.rate,
        base_amount=payload.base_amount,
        calculated_amount=payload.base_amount * payload.rate / 100,
        source_evidence=payload.source_evidence,
    )
    db.add(component)
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="duty_component",
        entity_id=component.id,
        action="duty_component.add",
        new_value=payload.model_dump(mode="json"),
        audit_id=audit_id,
    )
    db.commit()
    db.refresh(component)
    return component
