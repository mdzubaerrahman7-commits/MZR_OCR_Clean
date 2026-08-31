# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This repository now holds two unrelated things:

1. **The BondAudit Platform** (`backend/`, `frontend/`, `docs/`, `docker-compose.yml`,
   `.github/workflows/ci.yml`) — an enterprise Customs Bond Import Audit application
   (FastAPI + Next.js), built from a master specification supplied as a `.docx` (not
   checked into the repo). See `README.md` for setup/run instructions and
   `docs/ARCHITECTURE.md` / `docs/DATA_MODEL.md` for the design. This is a real
   software project with a build system, dependencies, and a pytest suite —
   the "no source code" framing below no longer applies to it.
2. **The original document-repository content** (unchanged, see below) — a scanned
   bond-consumption report and its OCR transcription/legal-reference annotation. This
   predates the application and is unrelated to it.

## Working on the BondAudit Platform

- `backend/app/services/*.py` are the audit engines (classification, matching,
  conversion, excess detection, duty assessment, reporting) — pure/DB-light Python,
  no FastAPI imports, each with its own pytest file in `backend/tests/`. Prefer
  extending these over putting business logic in `backend/app/api/routers/*.py`,
  which should stay a thin HTTP translation layer.
- Every mutating engine call must check `ensure_audit_not_locked` (see
  `backend/app/api/routers/audits.py`) and, where it represents a manual decision,
  call `app.services.audit_trail.record(...)` — this is the audit trail the spec
  requires (old value, new value, user, timestamp, reason).
- Money and quantity fields are `Decimal`/SQLAlchemy `Numeric`, never `float`. HS
  codes are strings, never numeric (leading zeros matter).
- **Known environment constraint**: this repository was built in a sandbox with no
  access to `pypi.org` or `registry.npmjs.org`, so `pip install` / `npm install` could
  not run there. If you're in an environment that also can't reach these registries,
  validate Python changes with `python3 -m py_compile` and TypeScript changes with the
  TypeScript compiler directly (ignore "cannot find module" errors for uninstalled
  packages — check for real `TS1xxx` syntax errors instead), and rely on
  `.github/workflows/ci.yml` to do the real `pip install`/`npm install` + test/build.
  If you do have registry access, just run `pytest` / `npm run build` normally.
- Backend tests: `cd backend && pytest -v`. Frontend: `cd frontend && npm install &&
  npm run typecheck && npm run build`.

## Working on the original OCR/document content

- `1Consumption January 2025_260625_221322_7.jpg` — the source scanned document: a bonded-warehouse **Consumption Report for January 2025** filed by RAHIMAFROOZ GLOBATT LIMITED (Ishwardi EPZ, Pakshey, Pabna, Bangladesh), covering export to RR Commodities (HK) Limited.
- `Consumption_Report_Jan2025_OCR_and_Legal_References.md` — a manually-transcribed OCR rendering of the scanned image, plus a corrected list of the Bangladeshi customs/VAT/EPZ laws applicable to this type of bond filing.

### Structure of the transcription file

`Consumption_Report_Jan2025_OCR_and_Legal_References.md` has two distinct parts — preserve this structure when editing:

1. **OCR transcription (English)** — a faithful reproduction of the source image:
   - `## Header` table: applicant/buyer identity, contract, export-bond, invoice, and C&F agent details.
   - `## Consumption Table`: line items of raw materials consumed against the bond, with opening/consumption/closing quantities. Column values (quantities, dates, reference numbers) must match the source image exactly — this is a transcription, not a summary, so don't "correct" figures without re-checking the image.
   - `## Signed By`: signatory details from the document.
2. **Legal basis section (Bangla)**, headed `আইনি ভিত্তি / বর্ণনা — সংশোধিত (Legal Basis — Corrected References)` — an independently-authored note (not part of the source image) listing the current Bangladeshi laws/rules governing bonded warehousing and EPZ exports (e.g. *The Customs Act, 2023*, *The Warehouse (Licensing) Rules, 2024*, VAT & SD Act/Rules, EPZ Rules 1984), replacing outdated references such as the *Customs Act, 1969*. This section is written in Bangla with a closing note flagging that a specific SRO number/date still needs verification against nbr.gov.bd.

### Conventions when editing

- Keep the transcription and the legal-references section clearly separated; do not blend transcribed source data with commentary.
- When updating legal references, verify citations (act names, years, SRO numbers/dates) against authoritative sources (e.g. nbr.gov.bd) rather than assuming — the existing note explicitly flags one unresolved SRO citation.
- Numeric/date fields in the Consumption Table should only be changed if verified against the source JPG image.
- The legal-references section is in Bangla; match its existing tone and terminology if extending it, rather than switching languages mid-section.
