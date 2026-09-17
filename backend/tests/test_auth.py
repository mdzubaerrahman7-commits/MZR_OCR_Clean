from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def test_bootstrap_admin_then_disabled(client: TestClient) -> None:
    resp = client.post(
        "/api/auth/bootstrap-admin",
        json={"email": "root@example.com", "password": "password123", "full_name": "Root Admin"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "administrator"

    # Bootstrap must refuse once a user exists — otherwise it's a privilege-escalation hole.
    resp2 = client.post(
        "/api/auth/bootstrap-admin",
        json={"email": "second@example.com", "password": "password123", "full_name": "Second"},
    )
    assert resp2.status_code == 403


def test_login_and_me(client: TestClient) -> None:
    client.post(
        "/api/auth/bootstrap-admin",
        json={"email": "root@example.com", "password": "password123", "full_name": "Root Admin"},
    )
    resp = client.post("/api/auth/login", json={"email": "root@example.com", "password": "password123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "root@example.com"


def test_login_wrong_password_rejected(client: TestClient) -> None:
    client.post(
        "/api/auth/bootstrap-admin",
        json={"email": "root@example.com", "password": "password123", "full_name": "Root Admin"},
    )
    resp = client.post("/api/auth/login", json={"email": "root@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_me_requires_token(client: TestClient) -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_register_requires_admin_permission(client: TestClient, auditor_headers: dict) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "password123", "full_name": "New", "role": "viewer"},
        headers=auditor_headers,
    )
    assert resp.status_code == 403


def test_register_as_admin_succeeds(client: TestClient, admin_headers: dict) -> None:
    resp = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "password123", "full_name": "New", "role": "viewer"},
        headers=admin_headers,
    )
    assert resp.status_code == 201


def test_list_users_requires_admin_permission(client: TestClient, auditor_headers: dict) -> None:
    resp = client.get("/api/auth/users", headers=auditor_headers)
    assert resp.status_code == 403


def test_list_users_as_admin(client: TestClient, admin_headers: dict, admin_user: User) -> None:
    resp = client.get("/api/auth/users", headers=admin_headers)
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert admin_user.email in emails


def test_reset_password_requires_admin_permission(
    client: TestClient, auditor_headers: dict, viewer_user: User
) -> None:
    resp = client.post(
        f"/api/auth/users/{viewer_user.id}/reset-password",
        json={"new_password": "brandnewpass123"},
        headers=auditor_headers,
    )
    assert resp.status_code == 403


def test_reset_password_missing_user_404s(client: TestClient, admin_headers: dict) -> None:
    resp = client.post(
        "/api/auth/users/does-not-exist/reset-password",
        json={"new_password": "brandnewpass123"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_reset_password_as_admin_then_login_with_new_password(
    client: TestClient, admin_headers: dict, viewer_user: User
) -> None:
    resp = client.post(
        f"/api/auth/users/{viewer_user.id}/reset-password",
        json={"new_password": "brandnewpass123", "reason": "user forgot their password"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == viewer_user.email

    # Old password no longer works, new one does.
    old = client.post("/api/auth/login", json={"email": viewer_user.email, "password": "password123"})
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"email": viewer_user.email, "password": "brandnewpass123"})
    assert new.status_code == 200
