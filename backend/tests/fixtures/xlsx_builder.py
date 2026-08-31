"""Tiny in-memory .xlsx builder for tests — avoids checking binary fixture files
into the repo. Every test that needs a spreadsheet builds it here from plain rows."""

import io

import openpyxl


def build_workbook_bytes(sheets: dict[str, list[list]]) -> bytes:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for sheet_name, rows in sheets.items():
        sheet = workbook.create_sheet(title=sheet_name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
