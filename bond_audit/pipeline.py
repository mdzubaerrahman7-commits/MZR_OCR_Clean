"""End-to-end pipeline: scanned bond consumption report -> OCR -> cleaned
structured data -> audited Excel report.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from . import ocr_engine
from .audit import RowAudit, audit_rows
from .export import write_cleaned_data, write_excel_report
from .grid import detect_grid
from .header_fields import extract_header_fields
from .table_extractor import extract_table

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    source_file: Path
    ocr_text_path: Path
    cleaned_data_path: Path
    excel_path: Path
    rows: list[dict]
    audits: list[RowAudit]


class NoTableFoundError(RuntimeError):
    pass


def process_file(
    input_path: Path,
    ocr_output_dir: Path,
    cleaned_data_dir: Path,
    excel_dir: Path,
) -> list[PipelineResult]:
    """Process one input file (image or multi-page PDF) and write outputs for
    every page that contains a bordered table.
    """
    pages = ocr_engine.load_pages(input_path)
    results: list[PipelineResult] = []

    for page_num, page in enumerate(pages, start=1):
        stem = input_path.stem if len(pages) == 1 else f"{input_path.stem}_p{page_num}"
        gray = ocr_engine.to_gray(page)

        full_text = ocr_engine.ocr_full_page_text(gray)
        ocr_text_path = ocr_output_dir / f"{stem}.txt"
        ocr_text_path.parent.mkdir(parents=True, exist_ok=True)
        ocr_text_path.write_text(full_text)

        grid = detect_grid(gray)
        if grid is None or grid.n_rows < 2 or grid.n_cols < 2:
            logger.warning("No bordered table detected on %s (page %s); skipping table audit.", input_path, page_num)
            continue

        table = extract_table(gray, grid)
        header_fields = extract_header_fields(full_text)
        audits = audit_rows(table.rows)

        cleaned_data_path = cleaned_data_dir / f"{stem}.json"
        write_cleaned_data(cleaned_data_path, str(input_path), header_fields, table.rows, audits)

        excel_path = excel_dir / f"{stem}.xlsx"
        write_excel_report(excel_path, str(input_path), header_fields, table.rows, audits)

        results.append(
            PipelineResult(
                source_file=input_path,
                ocr_text_path=ocr_text_path,
                cleaned_data_path=cleaned_data_path,
                excel_path=excel_path,
                rows=table.rows,
                audits=audits,
            )
        )

    if not results:
        raise NoTableFoundError(f"No bordered table found in {input_path}")

    return results
