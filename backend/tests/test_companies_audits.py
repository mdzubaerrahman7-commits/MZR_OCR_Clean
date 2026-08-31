from fastapi.testclient import TestClient


def _create_company(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/companies",
        json={
            "name": "RAHIMAFROOZ GLOBATT LIMITED",
            "bin_number": "000000000-0101",
            "bond_license_number": "BOND-2025-001",
            "facility_type": "epz",
            "address": "Ishwardi EPZ, Pakshey, Pabna, Bangladesh",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_list_company(client: TestClient, admin_headers: dict) -> None:
    company = _create_company(client, admin_headers)
    assert company["name"] == "RAHIMAFROOZ GLOBATT LIMITED"

    listed = client.get("/api/companies", headers=admin_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_viewer_cannot_create_company(client: TestClient, viewer_headers: dict) -> None:
    resp = client.post(
        "/api/companies",
        json={"name": "X", "bin_number": "1", "bond_license_number": "1"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


def test_create_audit_validates_period_order(client: TestClient, admin_headers: dict) -> None:
    company = _create_company(client, admin_headers)
    resp = client.post(
        "/api/audits",
        json={
            "company_id": company["id"],
            "audit_code": "AUD-2025-01",
            "title": "January 2025 Import Audit",
            "audit_period_start": "2025-01-31",
            "audit_period_end": "2025-01-01",  # invalid: end before start
            "entitlement_period_start": "2024-07-01",
            "entitlement_period_end": "2025-06-30",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_create_and_lock_audit(client: TestClient, admin_headers: dict) -> None:
    company = _create_company(client, admin_headers)
    resp = client.post(
        "/api/audits",
        json={
            "company_id": company["id"],
            "audit_code": "AUD-2025-01",
            "title": "January 2025 Import Audit",
            "audit_period_start": "2025-01-01",
            "audit_period_end": "2025-01-31",
            "entitlement_period_start": "2024-07-01",
            "entitlement_period_end": "2025-06-30",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    audit = resp.json()
    assert audit["status"] == "draft"

    lock_resp = client.post(f"/api/audits/{audit['id']}/lock", json={"reason": "period closed"}, headers=admin_headers)
    assert lock_resp.status_code == 200
    assert lock_resp.json()["status"] == "locked"

    # Locking again must fail — an audit is not re-lockable/unlockable through this endpoint.
    second_lock = client.post(f"/api/audits/{audit['id']}/lock", json={}, headers=admin_headers)
    assert second_lock.status_code == 409


def test_audit_for_missing_company_404s(client: TestClient, admin_headers: dict) -> None:
    resp = client.post(
        "/api/audits",
        json={
            "company_id": "does-not-exist",
            "audit_code": "AUD-2025-01",
            "title": "January 2025 Import Audit",
            "audit_period_start": "2025-01-01",
            "audit_period_end": "2025-01-31",
            "entitlement_period_start": "2024-07-01",
            "entitlement_period_end": "2025-06-30",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 404
