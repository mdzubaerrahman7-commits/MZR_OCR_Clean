from pydantic import BaseModel

from app.schemas.common import TimestampedORMBase


class CompanyCreate(BaseModel):
    name: str
    bin_number: str
    bond_license_number: str
    facility_type: str = "bonded_warehouse"
    address: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    bin_number: str | None = None
    bond_license_number: str | None = None
    facility_type: str | None = None
    address: str | None = None


class CompanyOut(TimestampedORMBase):
    name: str
    bin_number: str
    bond_license_number: str
    facility_type: str
    address: str | None = None
