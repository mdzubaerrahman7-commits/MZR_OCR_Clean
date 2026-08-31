from fastapi.testclient import TestClient

from tests.fixtures.xlsx_builder import build_workbook_bytes
from tests.test_workflow_end_to_end import _setup_audit, _upload_and_confirm

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _build_minimal_audit_with_a_non_entitled_import(client: TestClient, headers: dict) -> str:
    audit = _setup_audit(client, headers)
    audit_id = audit["id"]

    entitlement_xlsx = build_workbook_bytes(
        {"Entitlement": [["Group", "Material", "HS Code", "Unit", "Annual", "Enhanced"], ["Resins", "Resin A", "3902.10.00", "KG", 1000, 0]]}
    )
    _upload_and_confirm(
        client, headers, audit_id, "entitlement_sheet", entitlement_xlsx, "Entitlement",
        [
            {"source_header": "Group", "target_field": "group_name"},
            {"source_header": "Material", "target_field": "material_name"},
            {"source_header": "HS Code", "target_field": "hs_code"},
            {"source_header": "Unit", "target_field": "entitlement_unit"},
            {"source_header": "Annual", "target_field": "annual_entitlement_qty"},
            {"source_header": "Enhanced", "target_field": "enhanced_entitlement_qty"},
        ],
    )
    entitlement_doc_id = next(d["id"] for d in client.get(f"/api/audits/{audit_id}/documents", headers=headers).json() if d["document_type"] == "entitlement_sheet")
    client.post(f"/api/audits/{audit_id}/entitlement/parse", json={"source_document_id": entitlement_doc_id, "sheet_name": "Entitlement"}, headers=headers)

    # An import with an HS code that has no entitlement mapping -> non-entitled finding.
    import_xlsx = build_workbook_bytes(
        {
            "Imports": [
                ["BE No", "BE Date", "Description", "HS Code", "Quantity", "Unit", "Currency", "Value"],
                ["C-9001", "2025-01-10", "Unmapped Chemical", "2929.90.00", 200, "KG", "USD", 1000],
            ]
        }
    )
    _upload_and_confirm(
        client, headers, audit_id, "import_mis", import_xlsx, "Imports",
        [
            {"source_header": "BE No", "target_field": "be_number"},
            {"source_header": "BE Date", "target_field": "be_date"},
            {"source_header": "Description", "target_field": "item_description"},
            {"source_header": "HS Code", "target_field": "hs_code"},
            {"source_header": "Quantity", "target_field": "declared_quantity"},
            {"source_header": "Unit", "target_field": "declared_unit"},
            {"source_header": "Currency", "target_field": "original_currency"},
            {"source_header": "Value", "target_field": "original_currency_value"},
        ],
    )
    import_doc_id = next(d["id"] for d in client.get(f"/api/audits/{audit_id}/documents", headers=headers).json() if d["document_type"] == "import_mis")
    client.post(f"/api/audits/{audit_id}/imports/parse", json={"source_document_id": import_doc_id, "sheet_name": "Imports"}, headers=headers)

    # The HS code doesn't match anything, so classification lands on Unknown and the
    # transaction never becomes a raw-material match candidate — force it to Raw
    # Material via the manual-override path so detect-excess treats it as non-entitled.
    txn = client.get(f"/api/audits/{audit_id}/imports", headers=headers).json()[0]
    client.patch(
        f"/api/audits/{audit_id}/imports/{txn['id']}/classification",
        json={"classification": "raw_material", "reason": "Auditor review: confirmed raw material despite unmapped HS code"},
        headers=headers,
    )
    client.post(f"/api/audits/{audit_id}/detect-excess", headers=headers)
    client.post(f"/api/audits/{audit_id}/generate-findings", headers=headers)
    return audit_id


def test_generate_findings_and_download_reports(client: TestClient, admin_headers: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    audit_id = _build_minimal_audit_with_a_non_entitled_import(client, admin_headers)

    findings = client.get(f"/api/audits/{audit_id}/findings", headers=admin_headers).json()
    assert len(findings) == 1
    assert findings[0]["issue_type"] == "non_entitled"

    for output_code, endpoint in [("OUTPUT_01", "output-01"), ("OUTPUT_05", "output-05"), ("OUTPUT_07", "output-07")]:
        resp = client.post(f"/api/audits/{audit_id}/reports/{endpoint}", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == XLSX_MEDIA_TYPE
        assert len(resp.content) > 0

    history = client.get(f"/api/audits/{audit_id}/reports/history", headers=admin_headers).json()
    assert {h["output_code"] for h in history} == {"OUTPUT_01", "OUTPUT_05", "OUTPUT_07"}

    get_settings.cache_clear()


def test_finding_review_workflow(client: TestClient, admin_headers: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    audit_id = _build_minimal_audit_with_a_non_entitled_import(client, admin_headers)
    finding = client.get(f"/api/audits/{audit_id}/findings", headers=admin_headers).json()[0]

    resp = client.patch(
        f"/api/audits/{audit_id}/findings/{finding['id']}/review",
        json={"decision": "approved", "reason": "Confirmed against B/E copy"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["review_status"] == "approved"
    assert resp.json()["reviewed_by"] is not None

    # Regenerating findings must not reset the reviewer's decision.
    client.post(f"/api/audits/{audit_id}/generate-findings", headers=admin_headers)
    findings_after = client.get(f"/api/audits/{audit_id}/findings", headers=admin_headers).json()
    assert findings_after[0]["review_status"] == "approved"

    get_settings.cache_clear()
