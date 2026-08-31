from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import TimestampedORMBase


class BillOfEntryUpsert(BaseModel):
    be_number: str
    be_date: date
    conversion_evidence: str | None = None
    exchange_rate: Decimal | None = None
    exchange_rate_evidence: str | None = None
    kg_conversion_factor: Decimal | None = None
    kg_conversion_evidence: str | None = None
    entitlement_conversion_factor: Decimal | None = None
    entitlement_conversion_evidence: str | None = None
    assessable_value: Decimal | None = None


class DutyComponentIn(BaseModel):
    component_code: str
    rate: Decimal = Decimal("0")
    base_amount: Decimal = Decimal("0")
    source_evidence: str | None = None


class DutyComponentOut(TimestampedORMBase):
    bill_of_entry_id: str
    component_code: str
    rate: Decimal
    base_amount: Decimal
    calculated_amount: Decimal
    source_evidence: str | None = None


class BillOfEntryOut(TimestampedORMBase):
    audit_id: str
    be_number: str
    be_date: date
    conversion_evidence: str | None = None
    exchange_rate: Decimal | None = None
    exchange_rate_evidence: str | None = None
    kg_conversion_factor: Decimal | None = None
    kg_conversion_evidence: str | None = None
    entitlement_conversion_factor: Decimal | None = None
    entitlement_conversion_evidence: str | None = None
    assessable_value: Decimal | None = None
    duty_components: list[DutyComponentOut] = []
