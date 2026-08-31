from fastapi.testclient import TestClient

from tests.fixtures.xlsx_builder import build_workbook_bytes


def _create_company_and_audit(client: TestClient, headers: dict) -> dict:
    company = client.post(
        "/api/companies",
        json={"name": "Test Co", "bin_number": "1", "bond_license_number": "1"},
        headers=headers,
    ).json()
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
        headers=headers,
    ).json()
    return audit


def _sample_import_mis_xlsx() -> bytes:
    return build_workbook_bytes(
        {
            "Sheet1": [
                ["BE No", "BE Date", "Description", "HS Code", "Quantity", "Unit"],
                ["C1", "2025-01-05", "Copper Wire", "7408.11.00", 1000, "KG"],
            ]
        }
    )


def test_upload_detect_and_confirm_mapping(client: TestClient, admin_headers: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    audit = _create_company_and_audit(client, admin_headers)

    upload_resp = client.post(
        f"/api/audits/{audit['id']}/documents",
        data={"document_type": "import_mis"},
        files={"file": ("import_mis.xlsx", _sample_import_mis_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=admin_headers,
    )
    assert upload_resp.status_code == 201, upload_resp.text
    document = upload_resp.json()
    assert document["sheet_names"] == ["Sheet1"]

    suggestions_resp = client.get(
        f"/api/audits/{audit['id']}/documents/{document['id']}/mapping-suggestions",
        params={"sheet_name": "Sheet1"},
        headers=admin_headers,
    )
    assert suggestions_resp.status_code == 200
    suggestions = suggestions_resp.json()
    assert suggestions["header_row_index"] == 0
    be_no_suggestion = next(s for s in suggestions["suggestions"] if s["source_header"] == "BE No")
    assert be_no_suggestion["suggested_target_field"] == "be_number"

    confirm_resp = client.post(
        f"/api/audits/{audit['id']}/documents/{document['id']}/confirm-mapping",
        json={
            "sheet_name": "Sheet1",
            "mappings": [
                {"source_header": "BE No", "target_field": "be_number"},
                {"source_header": "HS Code", "target_field": "hs_code"},
            ],
            "save_as_template_name": "Standard Import MIS",
        },
        headers=admin_headers,
    )
    assert confirm_resp.status_code == 200, confirm_resp.text
    assert len(confirm_resp.json()) == 2

    templates_resp = client.get("/api/mapping-templates", params={"document_type": "import_mis"}, headers=admin_headers)
    assert templates_resp.status_code == 200
    assert templates_resp.json()[0]["name"] == "Standard Import MIS"

    get_settings.cache_clear()


def test_upload_rejects_on_locked_audit(client: TestClient, admin_headers: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    audit = _create_company_and_audit(client, admin_headers)
    client.post(f"/api/audits/{audit['id']}/lock", json={}, headers=admin_headers)

    resp = client.post(
        f"/api/audits/{audit['id']}/documents",
        data={"document_type": "import_mis"},
        files={"file": ("x.xlsx", _sample_import_mis_xlsx(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=admin_headers,
    )
    assert resp.status_code == 409

    get_settings.cache_clear()
