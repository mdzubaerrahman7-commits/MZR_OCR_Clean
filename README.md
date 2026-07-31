# MZR OCR Clean — Bond Consumption Report Audit

Takes scanned bond consumption reports (customs bonded-warehouse "Opening Qty
→ Consumption → Closing Qty" reconciliation reports, as filed by bonded
manufacturers like Rahimafrooz Globatt Limited), OCRs them, extracts the line
item table, and audits each row's arithmetic:

```
Closing Qty == Opening Qty − Consumption (with wastage)
```

Rows that don't reconcile — or that OCR couldn't confidently read — are
flagged for manual review instead of silently reported as correct.

## How it works

Rather than OCR-ing the whole page as free text (which loses column
alignment once numbers and text get jumbled together), the pipeline:

1. Detects the table's ruled border lines with OpenCV morphology
   (`bond_audit/grid.py`), so each cell can be cropped and OCR'd on its own.
2. OCRs each header cell and matches it to a canonical column
   (`bond_audit/table_extractor.py`), so column order can drift slightly
   between scans without breaking extraction.
3. OCRs each quantity cell at several render scales and keeps the value at
   least two scales agree on (falling back to the first scale otherwise) —
   this alone fixes most single-scale digit misreads on these low-resolution
   scans.
4. Applies a couple of report-specific parsing rules: every quantity has
   exactly 2 decimal places, so a comma that lands right before the last 2
   digits is a misread decimal point, not a thousands separator; and
   quantities are always non-negative, so a leading OCR-artifact dash is
   discarded rather than treated as a real sign.
5. Runs the reconciliation check on every row and writes:
   - `OCR_OUTPUT/<name>.txt` — raw whole-page OCR dump, for manual cross-check
     against the original scan.
   - `CLEANED_DATA/<name>.json` — structured header fields, every extracted
     row (both raw OCR text and parsed numeric value per quantity), and the
     per-row audit verdict.
   - `EXCEL_ANALYSIS/<name>.xlsx` — an "Extracted Data" sheet with every row
     color-coded by audit status (green = OK, red = mismatch, yellow =
     incomplete), and an "Audit Summary" sheet listing only the exceptions.

## Usage

```
pip install -r requirements.txt
# System dependencies (Ubuntu/Debian): tesseract-ocr, poppler-utils
sudo apt-get install -y tesseract-ocr poppler-utils

python3 main.py                      # processes every file in INPUT/
python3 main.py path/to/report.pdf   # or a single file / directory
python3 main.py -v                   # verbose logging
```

Drop scanned PDFs or images into `INPUT/` and run `python3 main.py`.

## Layout

```
bond_audit/
  grid.py             ruled-table border detection
  ocr_engine.py        page loading (PDF/image), preprocessing, cell OCR
  table_extractor.py   cell -> structured row, header-to-column matching, number parsing
  header_fields.py     best-effort extraction of the report's key/value header block
  audit.py             Opening/Consumption/Closing reconciliation check
  export.py            JSON + Excel report writers
  pipeline.py           orchestrates one input file end to end
  cli.py               command-line entry point
INPUT/                 put scanned PDFs/images here
OCR_OUTPUT/             raw per-page OCR text dumps
CLEANED_DATA/           structured JSON per input file
EXCEL_ANALYSIS/         audited Excel workbook per input file
```

## Known limitations

- Tuned against this report's exact column layout (SL No, In Bond No & Date,
  Import C-No & Date, Office Code, Item No, Name of Raw Materials, Unit,
  Opening Qty, Consumption with wastage, Consumption in KG for ASYCUDA,
  Closing Qty). A materially different table layout will need new header
  keywords in `table_extractor.COLUMN_KEYWORDS`.
- Header key/value fields above the table (Ex-Bond No, Export Qty, C&F Agent,
  etc.) are extracted best-effort by pattern rather than by reliably reading
  their (often stamp-overlapped) printed labels; the raw OCR text in
  `OCR_OUTPUT/` is the source of truth if these look off.
- OCR accuracy still depends on scan quality — always check rows flagged
  `MISMATCH` or `INCOMPLETE` in the Excel report against the original scan
  before treating the extracted numbers as final.
