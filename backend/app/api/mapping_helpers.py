from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import DocumentColumnMapping


def get_confirmed_mapping(db: Session, document_id: str, sheet_name: str) -> dict[str, str]:
    """The mapping an auditor confirmed via documents.confirm_mapping for this
    document/sheet. Shared by every engine that parses a spreadsheet (entitlement,
    import MIS) so 'no mapping confirmed' fails the same way everywhere."""
    rows = (
        db.query(DocumentColumnMapping)
        .filter(DocumentColumnMapping.source_document_id == document_id, DocumentColumnMapping.sheet_name == sheet_name)
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed column mapping for this document/sheet — confirm mapping before parsing (spec M03).",
        )
    return {row.source_header: row.target_field for row in rows}
