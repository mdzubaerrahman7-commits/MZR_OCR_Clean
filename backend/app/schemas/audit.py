from datetime import date, datetime

from pydantic import BaseModel, model_validator

from app.schemas.common import TimestampedORMBase


class AuditCreate(BaseModel):
    company_id: str
    audit_code: str
    title: str
    audit_period_start: date
    audit_period_end: date
    entitlement_period_start: date
    entitlement_period_end: date

    @model_validator(mode="after")
    def check_period_order(self) -> "AuditCreate":
        if self.audit_period_end < self.audit_period_start:
            raise ValueError("audit_period_end must not be before audit_period_start")
        if self.entitlement_period_end < self.entitlement_period_start:
            raise ValueError("entitlement_period_end must not be before entitlement_period_start")
        return self


class AuditOut(TimestampedORMBase):
    company_id: str
    audit_code: str
    title: str
    audit_period_start: date
    audit_period_end: date
    entitlement_period_start: date
    entitlement_period_end: date
    status: str
    created_by: str
    locked_at: datetime | None = None
    locked_by: str | None = None


class AuditLockRequest(BaseModel):
    reason: str | None = None
