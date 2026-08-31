from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.db.base import utcnow
from app.models.audit import Audit
from app.models.company import Company
from app.models.enums import AuditStatus
from app.models.user import User
from app.schemas.audit import AuditCreate, AuditLockRequest, AuditOut
from app.services import audit_trail

router = APIRouter(prefix="/api/audits", tags=["audits"])


@router.post("", response_model=AuditOut, status_code=status.HTTP_201_CREATED)
def create_audit(
    payload: AuditCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_COMPANIES)),
) -> Audit:
    if db.get(Company, payload.company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    audit = Audit(**payload.model_dump(), status=AuditStatus.DRAFT, created_by=current_user.id)
    db.add(audit)
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="audit",
        entity_id=audit.id,
        action="audit.create",
        new_value=payload.model_dump(mode="json"),
        audit_id=audit.id,
    )
    db.commit()
    db.refresh(audit)
    return audit


@router.get("", response_model=list[AuditOut])
def list_audits(
    company_id: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[Audit]:
    query = db.query(Audit)
    if company_id:
        query = query.filter(Audit.company_id == company_id)
    return query.order_by(Audit.created_at.desc()).all()


@router.get("/{audit_id}", response_model=AuditOut)
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> Audit:
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return audit


def get_audit_or_404(db: Session, audit_id: str) -> Audit:
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")
    return audit


def ensure_audit_not_locked(audit: Audit) -> None:
    """Non-negotiable rule (spec section 3/17): a locked/archived audit's evidence and
    results must not change. Every mutating engine call must check this first."""
    if audit.status == AuditStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audit is locked; unlock is not permitted by design (immutable archive)",
        )


@router.post("/{audit_id}/lock", response_model=AuditOut)
def lock_audit(
    audit_id: str,
    payload: AuditLockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.LOCK_AUDIT)),
) -> Audit:
    """Spec workflow step 17: Lock / Archive Audit Version. Locking is one-way — it is
    the archival boundary that makes a generated report set reproducible evidence."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    old_status = audit.status
    audit.status = AuditStatus.LOCKED
    audit.locked_at = utcnow()
    audit.locked_by = current_user.id
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="audit",
        entity_id=audit.id,
        action="audit.lock",
        old_value={"status": old_status},
        new_value={"status": audit.status},
        audit_id=audit.id,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(audit)
    return audit
