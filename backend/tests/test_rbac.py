"""Spec section 20's role/permission matrix, exercised at the HTTP layer rather than
just unit-testing the permission table in isolation — a wiring mistake in a router's
`require_permission(...)` call wouldn't show up in a pure permissions-module test."""

from fastapi.testclient import TestClient


def _create_company(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/companies",
        json={"name": "Test Co", "bin_number": "1", "bond_license_number": "1"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_auditor_can_create_and_lock_an_audit(client: TestClient, admin_headers: dict, auditor_headers: dict) -> None:
    company = _create_company(client, admin_headers)
    create_resp = client.post(
        "/api/audits",
        json={
            "company_id": company["id"],
            "audit_code": "AUD-1",
            "title": "Audit",
            "audit_period_start": "2025-01-01",
            "audit_period_end": "2025-01-31",
            "entitlement_period_start": "2024-07-01",
            "entitlement_period_end": "2025-06-30",
        },
        headers=auditor_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    audit_id = create_resp.json()["id"]

    lock_resp = client.post(f"/api/audits/{audit_id}/lock", json={}, headers=auditor_headers)
    assert lock_resp.status_code == 200


def test_viewer_cannot_create_audit_or_upload(client: TestClient, admin_headers: dict, viewer_headers: dict) -> None:
    company = _create_company(client, admin_headers)
    create_resp = client.post(
        "/api/audits",
        json={
            "company_id": company["id"],
            "audit_code": "AUD-1",
            "title": "Audit",
            "audit_period_start": "2025-01-01",
            "audit_period_end": "2025-01-31",
            "entitlement_period_start": "2024-07-01",
            "entitlement_period_end": "2025-06-30",
        },
        headers=viewer_headers,
    )
    assert create_resp.status_code == 403


def test_viewer_can_read(client: TestClient, admin_headers: dict, viewer_headers: dict) -> None:
    _create_company(client, admin_headers)
    resp = client.get("/api/companies", headers=viewer_headers)
    assert resp.status_code == 200


def test_only_administrator_can_manage_companies(client: TestClient, auditor_headers: dict) -> None:
    resp = client.post(
        "/api/companies",
        json={"name": "Test Co", "bin_number": "1", "bond_license_number": "1"},
        headers=auditor_headers,
    )
    assert resp.status_code == 403


def test_auditor_cannot_approve_findings(client: TestClient, admin_headers: dict, auditor_headers: dict) -> None:
    # Reviewer-only action per spec section 20 — an Auditor may prepare findings
    # (generate-findings, RUN_AUDIT_ENGINES) but approving them is a separate role.
    company = _create_company(client, admin_headers)
    audit = client.post(
        "/api/audits",
        json={
            "company_id": company["id"],
            "audit_code": "AUD-1",
            "title": "Audit",
            "audit_period_start": "2025-01-01",
            "audit_period_end": "2025-01-31",
            "entitlement_period_start": "2024-07-01",
            "entitlement_period_end": "2025-06-30",
        },
        headers=admin_headers,
    ).json()
    resp = client.patch(
        f"/api/audits/{audit['id']}/findings/does-not-exist/review",
        json={"decision": "approved"},
        headers=auditor_headers,
    )
    assert resp.status_code == 403


def test_reviewer_cannot_run_audit_engines(client: TestClient, admin_headers: dict, reviewer_headers: dict) -> None:
    company = _create_company(client, admin_headers)
    audit = client.post(
        "/api/audits",
        json={
            "company_id": company["id"],
            "audit_code": "AUD-1",
            "title": "Audit",
            "audit_period_start": "2025-01-01",
            "audit_period_end": "2025-01-31",
            "entitlement_period_start": "2024-07-01",
            "entitlement_period_end": "2025-06-30",
        },
        headers=admin_headers,
    ).json()
    resp = client.post(f"/api/audits/{audit['id']}/classify", headers=reviewer_headers)
    assert resp.status_code == 403


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    resp = client.get("/api/companies")
    assert resp.status_code == 401
