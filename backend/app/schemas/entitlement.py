from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import TimestampedORMBase


class ParseEntitlementRequest(BaseModel):
    source_document_id: str
    sheet_name: str


class EntitlementItemOut(TimestampedORMBase):
    group_id: str
    sequence_no: int
    material_name: str
    hs_code: str
    entitlement_unit: str
    annual_entitlement_qty: Decimal
    enhanced_entitlement_qty: Decimal
    total_entitlement_qty: Decimal
    active: bool
    source_row_number: int | None = None


class EntitlementGroupOut(TimestampedORMBase):
    audit_id: str
    sequence_no: int
    group_name: str
    group_code: str | None = None
    notes: str | None = None
    items: list[EntitlementItemOut] = []


class ParseEntitlementResult(BaseModel):
    groups_created: int
    items_created: int
    groups: list[EntitlementGroupOut]
