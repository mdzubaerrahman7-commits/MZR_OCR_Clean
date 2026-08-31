from pydantic import BaseModel, EmailStr, Field

from app.core.permissions import Role
from app.schemas.common import TimestampedORMBase


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: Role = Role.VIEWER


class UserOut(TimestampedORMBase):
    email: str
    full_name: str
    role: str
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
