# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This is a small **document repository**, not a software project — there is no source code, build system, package manifest, linter, or test suite. It holds a single scanned bond-consumption report and its OCR transcription/legal-reference annotation. There are no commands to build, lint, or test.

## Contents

- `1Consumption January 2025_260625_221322_7.jpg` — the source scanned document: a bonded-warehouse **Consumption Report for January 2025** filed by RAHIMAFROOZ GLOBATT LIMITED (Ishwardi EPZ, Pakshey, Pabna, Bangladesh), covering export to RR Commodities (HK) Limited.
- `Consumption_Report_Jan2025_OCR_and_Legal_References.md` — a manually-transcribed OCR rendering of the scanned image, plus a corrected list of the Bangladeshi customs/VAT/EPZ laws applicable to this type of bond filing.

## Structure of the transcription file

`Consumption_Report_Jan2025_OCR_and_Legal_References.md` has two distinct parts — preserve this structure when editing:

1. **OCR transcription (English)** — a faithful reproduction of the source image:
   - `## Header` table: applicant/buyer identity, contract, export-bond, invoice, and C&F agent details.
   - `## Consumption Table`: line items of raw materials consumed against the bond, with opening/consumption/closing quantities. Column values (quantities, dates, reference numbers) must match the source image exactly — this is a transcription, not a summary, so don't "correct" figures without re-checking the image.
   - `## Signed By`: signatory details from the document.
2. **Legal basis section (Bangla)**, headed `আইনি ভিত্তি / বর্ণনা — সংশোধিত (Legal Basis — Corrected References)` — an independently-authored note (not part of the source image) listing the current Bangladeshi laws/rules governing bonded warehousing and EPZ exports (e.g. *The Customs Act, 2023*, *The Warehouse (Licensing) Rules, 2024*, VAT & SD Act/Rules, EPZ Rules 1984), replacing outdated references such as the *Customs Act, 1969*. This section is written in Bangla with a closing note flagging that a specific SRO number/date still needs verification against nbr.gov.bd.

## Conventions when editing

- Keep the transcription and the legal-references section clearly separated; do not blend transcribed source data with commentary.
- When updating legal references, verify citations (act names, years, SRO numbers/dates) against authoritative sources (e.g. nbr.gov.bd) rather than assuming — the existing note explicitly flags one unresolved SRO citation.
- Numeric/date fields in the Consumption Table should only be changed if verified against the source JPG image.
- The legal-references section is in Bangla; match its existing tone and terminology if extending it, rather than switching languages mid-section.
