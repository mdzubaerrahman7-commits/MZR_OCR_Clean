from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.api.routers.audits import ensure_audit_not_locked, get_audit_or_404
from app.core.permissions import Permission
from app.models.document import ColumnMappingTemplate, ColumnMappingTemplateField, DocumentColumnMapping, SourceDocument
from app.models.enums import DocumentType
from app.models.user import User
from app.schemas.document import (
    ColumnMappingSuggestionsOut,
    ConfirmMappingRequest,
    DocumentColumnMappingOut,
    HeaderDetectionOut,
    MappingSuggestionOut,
    MappingTemplateOut,
    SourceDocumentOut,
)
from app.services import audit_trail, excel_intelligence, storage

router = APIRouter(prefix="/api/audits/{audit_id}/documents", tags=["documents"])
templates_router = APIRouter(prefix="/api/mapping-templates", tags=["mapping-templates"])


@router.post("", response_model=SourceDocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    audit_id: str,
    file: UploadFile,
    document_type: DocumentType = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.UPLOAD_DOCUMENTS)),
) -> SourceDocument:
    """M02 — Document Upload Center. The file is written to immutable storage before
    anything else touches it, and every re-upload creates a new row (supersedes_id)
    rather than overwriting: raw evidence must never be silently modified (spec section 3)."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)

    content = await file.read()
    checksum = storage.sha256_checksum(content)
    key = storage.build_storage_key(audit_id, checksum, file.filename or "upload.xlsx")
    backend = storage.get_storage_backend()
    backend.write(key, content)

    try:
        sheet_names = excel_intelligence.list_sheets(content)
    except Exception as exc:  # noqa: BLE001 — surface as a 422, not a 500
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not read spreadsheet: {exc}") from exc

    previous = (
        db.query(SourceDocument)
        .filter(SourceDocument.audit_id == audit_id, SourceDocument.document_type == document_type)
        .order_by(SourceDocument.uploaded_at.desc())
        .first()
    )

    document = SourceDocument(
        audit_id=audit_id,
        document_type=document_type,
        original_filename=file.filename or "upload.xlsx",
        storage_key=key,
        checksum_sha256=checksum,
        content_type=file.content_type,
        sheet_names=sheet_names,
        uploaded_by=current_user.id,
        supersedes_id=previous.id if previous else None,
    )
    db.add(document)
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="source_document",
        entity_id=document.id,
        action="document.upload",
        new_value={"filename": document.original_filename, "document_type": document_type, "checksum": checksum},
        audit_id=audit_id,
    )
    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[SourceDocumentOut])
def list_documents(
    audit_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[SourceDocument]:
    get_audit_or_404(db, audit_id)
    return (
        db.query(SourceDocument)
        .filter(SourceDocument.audit_id == audit_id)
        .order_by(SourceDocument.uploaded_at.desc())
        .all()
    )


def get_document_or_404(db: Session, audit_id: str, document_id: str) -> SourceDocument:
    document = db.get(SourceDocument, document_id)
    if document is None or document.audit_id != audit_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.get("/{document_id}/sheets", response_model=list[str])
def list_document_sheets(
    audit_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[str]:
    document = get_document_or_404(db, audit_id, document_id)
    return document.sheet_names or []


@router.get("/{document_id}/mapping-suggestions", response_model=ColumnMappingSuggestionsOut)
def get_mapping_suggestions(
    audit_id: str,
    document_id: str,
    sheet_name: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.MAP_DATA)),
) -> ColumnMappingSuggestionsOut:
    """M03: detect headers, suggest column mapping. Read-only — nothing is persisted
    until the auditor calls confirm-mapping."""
    document = get_document_or_404(db, audit_id, document_id)
    backend = storage.get_storage_backend()
    content = backend.read(document.storage_key)

    detection = excel_intelligence.detect_header_row(content, sheet_name)
    suggestions = excel_intelligence.suggest_column_mapping(detection.headers, DocumentType(document.document_type))
    preview = excel_intelligence.read_rows(content, sheet_name, detection.header_row_index, detection.headers, limit=10)

    return ColumnMappingSuggestionsOut(
        sheet_name=sheet_name,
        header_row_index=detection.header_row_index,
        available_target_fields=sorted(excel_intelligence.CANONICAL_FIELDS.get(DocumentType(document.document_type), {})),
        suggestions=[MappingSuggestionOut(**s.__dict__) for s in suggestions],
        preview_rows=[row.values for row in preview],
    )


@router.post("/{document_id}/confirm-mapping", response_model=list[DocumentColumnMappingOut])
def confirm_mapping(
    audit_id: str,
    document_id: str,
    payload: ConfirmMappingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MAP_DATA)),
) -> list[DocumentColumnMapping]:
    """M03: 'Allow auditor confirmation.' This is the only way a mapping becomes
    authoritative — AI/heuristic suggestions never apply themselves (spec section 10's
    'never bypass auditor approval' rule applies here too)."""
    audit = get_audit_or_404(db, audit_id)
    ensure_audit_not_locked(audit)
    document = get_document_or_404(db, audit_id, document_id)

    # Replace any prior confirmed mapping for this sheet — confirmation is a decision,
    # and the old decision is preserved in the audit trail below, not silently lost.
    old_mappings = (
        db.query(DocumentColumnMapping)
        .filter(DocumentColumnMapping.source_document_id == document_id, DocumentColumnMapping.sheet_name == payload.sheet_name)
        .all()
    )
    old_value = [{"source_header": m.source_header, "target_field": m.target_field} for m in old_mappings]
    for m in old_mappings:
        db.delete(m)

    created: list[DocumentColumnMapping] = []
    for entry in payload.mappings:
        mapping = DocumentColumnMapping(
            source_document_id=document_id,
            sheet_name=payload.sheet_name,
            source_header=entry.source_header,
            target_field=entry.target_field,
            confirmed_by=current_user.id,
        )
        db.add(mapping)
        created.append(mapping)
    db.flush()

    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="document_column_mapping",
        entity_id=document_id,
        action="mapping.confirm",
        old_value={"mappings": old_value},
        new_value={"mappings": [{"source_header": e.source_header, "target_field": e.target_field} for e in payload.mappings]},
        audit_id=audit_id,
    )

    if payload.save_as_template_name:
        template = ColumnMappingTemplate(
            name=payload.save_as_template_name,
            document_type=document.document_type,
            company_id=audit.company_id,
            created_by=current_user.id,
        )
        db.add(template)
        db.flush()
        for idx, entry in enumerate(payload.mappings):
            db.add(
                ColumnMappingTemplateField(
                    template_id=template.id,
                    sequence_no=idx,
                    source_header=entry.source_header,
                    target_field=entry.target_field,
                )
            )

    db.commit()
    for m in created:
        db.refresh(m)
    return created


@templates_router.get("", response_model=list[MappingTemplateOut])
def list_mapping_templates(
    document_type: DocumentType | None = None,
    company_id: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[ColumnMappingTemplate]:
    query = db.query(ColumnMappingTemplate)
    if document_type:
        query = query.filter(ColumnMappingTemplate.document_type == document_type)
    if company_id:
        query = query.filter(ColumnMappingTemplate.company_id == company_id)
    return query.order_by(ColumnMappingTemplate.name).all()
