"""Import every model module so Alembic's autogenerate and Base.metadata see them all."""

from app.models.audit import Audit
from app.models.audit_log import AuditLogEntry
from app.models.bill_of_entry import BillOfEntry, DutyComponent
from app.models.company import Company
from app.models.document import ColumnMappingTemplate, ColumnMappingTemplateField, DocumentColumnMapping, SourceDocument
from app.models.entitlement import EntitlementGroup, EntitlementItem
from app.models.finding import Finding
from app.models.import_transaction import ImportTransaction
from app.models.report import GeneratedReport
from app.models.user import User

__all__ = [
    "Audit",
    "AuditLogEntry",
    "BillOfEntry",
    "DutyComponent",
    "Company",
    "ColumnMappingTemplate",
    "ColumnMappingTemplateField",
    "DocumentColumnMapping",
    "SourceDocument",
    "EntitlementGroup",
    "EntitlementItem",
    "Finding",
    "ImportTransaction",
    "GeneratedReport",
    "User",
]
