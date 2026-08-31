"""End-to-end coverage of the main workflow (spec section 22, steps 1-14): create
company/audit, upload + map + parse entitlement and import MIS, match, convert,
detect excess, and read back the exception dashboard. This is the integration test
that pins the whole pipeline together, not just each engine in isolation."""

from decimal import Decimal

from fastapi.testclient import TestClient

from tests.fixtures.xlsx_builder import build_workbook_bytes


def _setup_audit(client: TestClient, headers: dict) -> dict:
    company = client.post(
        "/api/companies",
        json={"name": "RAHIMAFROOZ GLOBATT LIMITED", "bin_number": "1", "bond_license_number": "1", "facility_type": "epz"},
        headers=headers,
    ).json()
    audit = client.post(
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
        headers=headers,
    ).json()
    return audit


def _upload_and_confirm(client, headers, audit_id, document_type, xlsx_bytes, sheet_name, mappings):
    upload = client.post(
        f"/api/audits/{audit_id}/documents",
        data={"document_type": document_type},
        files={"file": ("f.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()

    confirm = client.post(
        f"/api/audits/{audit_id}/documents/{document['id']}/confirm-mapping",
        json={"sheet_name": sheet_name, "mappings": mappings},
        headers=headers,
    )
    assert confirm.status_code == 200, confirm.text
    return document


def test_full_import_audit_workflow(client: TestClient, admin_headers: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()

    audit = _setup_audit(client, admin_headers)
    audit_id = audit["id"]

    # --- Entitlement sheet ---
    entitlement_xlsx = build_workbook_bytes(
        {
            "Entitlement": [
                ["Group", "SL", "Material", "HS Code", "Unit", "Annual", "Enhanced"],
                ["Polymer & Resins", 1, "Polypropylene Resin", "3902.10.00", "KG", 10000, 0],
            ]
        }
    )
    _upload_and_confirm(
        client,
        admin_headers,
        audit_id,
        "entitlement_sheet",
        entitlement_xlsx,
        "Entitlement",
        [
            {"source_header": "Group", "target_field": "group_name"},
            {"source_header": "SL", "target_field": "sequence_no"},
            {"source_header": "Material", "target_field": "material_name"},
            {"source_header": "HS Code", "target_field": "hs_code"},
            {"source_header": "Unit", "target_field": "entitlement_unit"},
            {"source_header": "Annual", "target_field": "annual_entitlement_qty"},
            {"source_header": "Enhanced", "target_field": "enhanced_entitlement_qty"},
        ],
    )
    entitlement_docs = client.get(f"/api/audits/{audit_id}/documents", headers=admin_headers).json()
    entitlement_doc_id = next(d["id"] for d in entitlement_docs if d["document_type"] == "entitlement_sheet")

    parse_entitlement = client.post(
        f"/api/audits/{audit_id}/entitlement/parse",
        json={"source_document_id": entitlement_doc_id, "sheet_name": "Entitlement"},
        headers=admin_headers,
    )
    assert parse_entitlement.status_code == 200, parse_entitlement.text
    assert parse_entitlement.json()["groups_created"] == 1
    assert parse_entitlement.json()["items_created"] == 1
    entitlement_item_id = parse_entitlement.json()["groups"][0]["items"][0]["id"]

    # --- Import MIS: two B/Es for the same material, 9,500 then 1,000 KG ---
    import_mis_xlsx = build_workbook_bytes(
        {
            "Imports": [
                ["BE No", "BE Date", "Description", "HS Code", "Quantity", "Unit", "Currency", "Value"],
                ["C-0001", "2025-01-05", "Polypropylene Resin", "3902.10.00", 9500, "KG", "USD", 47500],
                ["C-0002", "2025-01-20", "Polypropylene Resin", "3902.10.00", 1000, "KG", "USD", 5000],
            ]
        }
    )
    _upload_and_confirm(
        client,
        admin_headers,
        audit_id,
        "import_mis",
        import_mis_xlsx,
        "Imports",
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
    import_docs = client.get(f"/api/audits/{audit_id}/documents", headers=admin_headers).json()
    import_doc_id = next(d["id"] for d in import_docs if d["document_type"] == "import_mis")

    parse_imports = client.post(
        f"/api/audits/{audit_id}/imports/parse",
        json={"source_document_id": import_doc_id, "sheet_name": "Imports"},
        headers=admin_headers,
    )
    assert parse_imports.status_code == 200, parse_imports.text
    assert parse_imports.json()["in_period_count"] == 2
    assert parse_imports.json()["classification_breakdown"].get("raw_material") == 2

    # --- Matching ---
    match_result = client.post(f"/api/audits/{audit_id}/match-entitlements", headers=admin_headers)
    assert match_result.status_code == 200, match_result.text
    assert match_result.json()["suggested_count"] == 2

    transactions = client.get(f"/api/audits/{audit_id}/imports", headers=admin_headers).json()
    assert len(transactions) == 2
    for txn in transactions:
        assert txn["match_status"] == "suggested"
        assert txn["entitlement_item_id"] == entitlement_item_id
        confirm = client.post(
            f"/api/audits/{audit_id}/imports/{txn['id']}/match/confirm",
            json={"decision": "approved"},
            headers=admin_headers,
        )
        assert confirm.status_code == 200, confirm.text
        assert confirm.json()["match_status"] == "approved"

    # --- Conversion (same units, USD currency -> no B/E evidence needed) ---
    conversion_result = client.post(f"/api/audits/{audit_id}/calculate-conversions", headers=admin_headers)
    assert conversion_result.status_code == 200, conversion_result.text
    assert conversion_result.json()["fully_converted_count"] == 2

    # --- Excess detection: 9,500 within, 1,000 -> 500 allowed / 500 excess ---
    excess_result = client.post(f"/api/audits/{audit_id}/detect-excess", headers=admin_headers)
    assert excess_result.status_code == 200, excess_result.text
    assert excess_result.json()["within_entitlement_count"] == 1
    assert excess_result.json()["partial_excess_count"] == 1

    transactions = client.get(f"/api/audits/{audit_id}/imports", headers=admin_headers).json()
    by_be = {t["be_number"]: t for t in transactions}
    assert by_be["C-0001"]["excess_status"] == "within_entitlement"
    assert by_be["C-0002"]["excess_status"] == "partial_excess"
    assert Decimal(str(by_be["C-0002"]["allowed_quantity"])) == Decimal("500")
    assert Decimal(str(by_be["C-0002"]["excess_quantity"])) == Decimal("500")

    # --- Exception dashboard ---
    dashboard = client.get(f"/api/audits/{audit_id}/exceptions", headers=admin_headers).json()
    assert dashboard["partial_excess_count"] == 1
    assert dashboard["non_entitled_count"] == 0

    get_settings.cache_clear()
