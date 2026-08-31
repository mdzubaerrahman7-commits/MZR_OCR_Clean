from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.permissions import Role
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.user import User


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _get_db_override() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def make_user(db_session: Session, *, role: Role, email: str = "user@example.com") -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        full_name="Test User",
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_user(db_session: Session) -> User:
    return make_user(db_session, role=Role.ADMINISTRATOR, email="admin@example.com")


@pytest.fixture()
def admin_headers(admin_user: User) -> dict[str, str]:
    return auth_headers(admin_user)


@pytest.fixture()
def auditor_user(db_session: Session) -> User:
    return make_user(db_session, role=Role.AUDITOR, email="auditor@example.com")


@pytest.fixture()
def auditor_headers(auditor_user: User) -> dict[str, str]:
    return auth_headers(auditor_user)


@pytest.fixture()
def viewer_user(db_session: Session) -> User:
    return make_user(db_session, role=Role.VIEWER, email="viewer@example.com")


@pytest.fixture()
def viewer_headers(viewer_user) -> dict[str, str]:
    return auth_headers(viewer_user)


@pytest.fixture()
def reviewer_user(db_session: Session) -> User:
    return make_user(db_session, role=Role.REVIEWER, email="reviewer@example.com")


@pytest.fixture()
def reviewer_headers(reviewer_user) -> dict[str, str]:
    return auth_headers(reviewer_user)
