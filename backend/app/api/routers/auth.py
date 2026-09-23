from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import LoginRequest, PasswordResetRequest, TokenResponse, UserCreate, UserOut
from app.services import audit_trail

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_permission(Permission.MANAGE_USERS)),
) -> User:
    """Administrator-only: create a new platform user with an explicit role (spec section 20)."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/bootstrap-admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create the first Administrator when no users exist yet. Disabled once any user exists,
    so it can never be used to escalate privileges after initial setup."""
    if db.query(User).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap is only available before the first user is created; use /register instead",
        )
    from app.core.permissions import Role

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=Role.ADMINISTRATOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(subject=user.id, role=user.role)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_permission(Permission.MANAGE_USERS)),
) -> list[User]:
    """Administrator-only: list platform users, e.g. to pick one for a password reset."""
    return db.query(User).order_by(User.email).all()


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: str,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission(Permission.MANAGE_USERS)),
) -> User:
    """Administrator-only: set a user's password directly. Stands in for self-service
    password recovery, which needs an email/SMTP integration this deployment doesn't
    have configured yet."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.hashed_password = hash_password(payload.new_password)
    audit_trail.record(
        db,
        user_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        action="password_reset",
        reason=payload.reason,
    )
    db.commit()
    db.refresh(user)
    return user
