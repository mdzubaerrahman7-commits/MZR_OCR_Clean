from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.mapping_helpers import get_confirmed_mapping
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.api.routers.documents import get_document_or_404
from app.core.permissions import Permission
from app.models.entitlement import EntitlementGroup, EntitlementItem
from app.models.user import User
from app.schemas.entitlement import EntitlementGroupOut, ParseEntitlementRequest, ParseEntitlementResult
from app.services import audit_trail, excel_intelligence, storage
from app.services.entitlement_engine import parse_entitlement_rows

router = APIRouter(prefix="/api/audits/{audit_id}/entitlement", tags=["entitlement"])


@router.post("/parse", response_model=ParseEntitlementResult)
def parse_entitlement(
    audit_id: str,
    payload: ParseEntitlementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RUN_AUDIT_ENGINES)),
) -> ParseEntitlementResult:
    """M04: build the entitlement master from a confirmed mapping. Re-running this
    replaces the current entitlement master (the underlying raw document/rows are
    untouched — only the derived group/item structure is regenerated), which is why
    it's logged to the audit trail with the prior state."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    document = get_document_or_404(db, audit_id, payload.source_document_id)

    column_mapping = get_confirmed_mapping(db, document.id, payload.sheet_name)
    backend = storage.get_storage_backend()
    content = backend.read(document.storage_key)
    detection = excel_intelligence.detect_header_row(content, payload.sheet_name)
    rows = excel_intelligence.read_rows(content, payload.sheet_name, detection.header_row_index, detection.headers)
    parsed_groups = parse_entitlement_rows(rows, column_mapping)

    existing_groups = db.query(EntitlementGroup).filter(EntitlementGroup.audit_id == audit_id).all()
    old_summary = {"group_count": len(existing_groups)}
    for g in existing_groups:
        db.delete(g)
    db.flush()

    created_groups: list[EntitlementGroup] = []
    items_created = 0
    for pg in parsed_groups:
        group = EntitlementGroup(
            audit_id=audit_id,
            sequence_no=pg.sequence_no,
            group_name=pg.group_name,
            group_code=pg.group_code,
            source_document_id=document.id,
        )
        db.add(group)
        db.flush()
        for pi in pg.items:
            db.add(
                EntitlementItem(
                    group_id=group.id,
                    sequence_no=pi.sequence_no,
                    material_name=pi.material_name,
                    hs_code=pi.hs_code,
                    entitlement_unit=pi.entitlement_unit,
                    annual_entitlement_qty=pi.annual_entitlement_qty,
                    enhanced_entitlement_qty=pi.enhanced_entitlement_qty,
                    total_entitlement_qty=pi.total_entitlement_qty,
                    source_document_id=document.id,
                    source_row_number=pi.row_number,
                )
            )
            items_created += 1
        created_groups.append(group)

    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="entitlement_master",
        entity_id=audit_id,
        action="entitlement.parse",
        old_value=old_summary,
        new_value={"group_count": len(created_groups), "item_count": items_created, "source_document_id": document.id},
        audit_id=audit_id,
    )
    db.commit()

    groups = (
        db.query(EntitlementGroup)
        .filter(EntitlementGroup.audit_id == audit_id)
        .order_by(EntitlementGroup.sequence_no)
        .all()
    )
    return ParseEntitlementResult(groups_created=len(created_groups), items_created=items_created, groups=groups)


@router.get("", response_model=list[EntitlementGroupOut])
def list_entitlement(
    audit_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[EntitlementGroup]:
    """Group order here is exactly entitlement_groups.sequence_no — never re-sorted
    (spec section 17)."""
    get_audit_or_404(db, audit_id)
    return (
        db.query(EntitlementGroup)
        .filter(EntitlementGroup.audit_id == audit_id)
        .order_by(EntitlementGroup.sequence_no)
        .all()
    )
