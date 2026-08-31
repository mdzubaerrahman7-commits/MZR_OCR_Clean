from app.models.enums import DocumentType
from app.services import excel_intelligence
from tests.fixtures.xlsx_builder import build_workbook_bytes


def _import_mis_bytes() -> bytes:
    return build_workbook_bytes(
        {
            "Import MIS": [
                ["RAHIMAFROOZ GLOBATT LIMITED"],
                ["Import MIS - January 2025"],
                [],
                ["BE No", "BE Date", "Description", "HS Code", "Quantity", "Unit", "Currency", "Value"],
                ["C12345", "2025-01-05", "Copper Wire", "7408.11.00", 1000, "KG", "USD", 5000],
                ["C12346", "2025-01-15", "Copper Wire", "7408.11.00", 500, "KG", "USD", 2500],
            ]
        }
    )


def test_list_sheets() -> None:
    content = _import_mis_bytes()
    assert excel_intelligence.list_sheets(content) == ["Import MIS"]


def test_detect_header_row_skips_title_rows() -> None:
    content = _import_mis_bytes()
    result = excel_intelligence.detect_header_row(content, "Import MIS")
    assert result.header_row_index == 3  # 0-based: row 4 in the sheet
    assert result.headers[0] == "BE No"
    assert "HS Code" in result.headers


def test_suggest_column_mapping_exact_and_fuzzy() -> None:
    headers = ["BE No", "BE Date", "Description", "HS Code", "Quantity", "Unit", "Currency", "Value"]
    suggestions = excel_intelligence.suggest_column_mapping(headers, DocumentType.IMPORT_MIS)
    by_header = {s.source_header: s for s in suggestions}

    assert by_header["BE No"].suggested_target_field == "be_number"
    assert by_header["BE No"].confidence == 1.0
    assert by_header["HS Code"].suggested_target_field == "hs_code"
    assert by_header["Description"].suggested_target_field == "item_description"
    assert by_header["Quantity"].suggested_target_field == "declared_quantity"


def test_suggest_column_mapping_unknown_header_returns_none() -> None:
    suggestions = excel_intelligence.suggest_column_mapping(["Totally Unrelated Column"], DocumentType.IMPORT_MIS)
    assert suggestions[0].suggested_target_field is None


def test_read_rows_skips_blank_rows_and_keys_by_header() -> None:
    content = _import_mis_bytes()
    detection = excel_intelligence.detect_header_row(content, "Import MIS")
    rows = excel_intelligence.read_rows(content, "Import MIS", detection.header_row_index, detection.headers)
    assert len(rows) == 2
    assert rows[0].values["BE No"] == "C12345"
    assert rows[0].values["HS Code"] == "7408.11.00"
    # Row numbers refer back to the real spreadsheet row — evidence must be traceable.
    assert rows[0].row_number == 5
    assert rows[1].row_number == 6
