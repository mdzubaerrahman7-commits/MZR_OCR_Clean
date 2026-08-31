from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyOut, CompanyUpdate
from app.services import audit_trail

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_COMPANIES)),
) -> Company:
    company = Company(**payload.model_dump())
    db.add(company)
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="company",
        entity_id=company.id,
        action="company.create",
        new_value=payload.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanyOut])
def list_companies(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> list[Company]:
    return db.query(Company).order_by(Company.name).all()


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission(Permission.READ)),
) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: str,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.MANAGE_COMPANIES)),
) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    old_value = {"name": company.name, "bin_number": company.bin_number, "bond_license_number": company.bond_license_number}
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(company, key, value)
    db.flush()
    audit_trail.record(
        db,
        user_id=current_user.id,
        entity_type="company",
        entity_id=company.id,
        action="company.update",
        old_value=old_value,
        new_value=updates,
    )
    db.commit()
    db.refresh(company)
    return company
