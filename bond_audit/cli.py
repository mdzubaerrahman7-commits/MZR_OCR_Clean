"""Command-line entry point for the bond audit pipeline."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .ocr_engine import IMAGE_SUFFIXES, PDF_SUFFIXES
from .pipeline import NoTableFoundError, process_file

SUPPORTED_SUFFIXES = IMAGE_SUFFIXES | PDF_SUFFIXES


def _collect_inputs(input_path: Path) -> list[Path]:
    if input_path.is_dir():
        return sorted(
            p for p in input_path.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES
        )
    return [input_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OCR a scanned bond consumption report, extract its table, "
        "and audit Opening/Consumption/Closing quantity reconciliation."
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=Path("INPUT"),
        help="Scanned PDF/image file, or a directory of them (default: INPUT/)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("."),
        help="Directory containing OCR_OUTPUT/CLEANED_DATA/EXCEL_ANALYSIS (default: current directory)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    ocr_output_dir = args.output_root / "OCR_OUTPUT"
    cleaned_data_dir = args.output_root / "CLEANED_DATA"
    excel_dir = args.output_root / "EXCEL_ANALYSIS"

    inputs = _collect_inputs(args.input)
    if not inputs:
        print(f"No supported input files found at {args.input}", file=sys.stderr)
        return 1

    exit_code = 0
    for path in inputs:
        try:
            results = process_file(path, ocr_output_dir, cleaned_data_dir, excel_dir)
        except NoTableFoundError as exc:
            print(f"[SKIPPED] {exc}", file=sys.stderr)
            exit_code = 1
            continue
        except Exception as exc:  # noqa: BLE001 - surface any failure per file, keep going
            print(f"[ERROR] {path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        for result in results:
            mismatches = sum(1 for a in result.audits if a.status == "MISMATCH")
            incomplete = sum(1 for a in result.audits if a.status == "INCOMPLETE")
            print(
                f"[OK] {path.name}: {len(result.audits)} line items, "
                f"{mismatches} mismatch(es), {incomplete} incomplete -> {result.excel_path}"
            )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
