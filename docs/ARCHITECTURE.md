# BondAudit Platform — Architecture

Source specification: `Claude-Ready Master Development Specification — Enterprise Customs
Bond Import Audit System, v1.0, Module 01: Import Audit` (supplied as a `.docx`, not
checked into the repo). This document is Claude's architecture analysis, written before
implementation as instructed by the spec's own section 25 ("Claude Implementation
Instruction").

## 1. Scope of this build

The spec names five future modules (Consumption Audit, Export Audit, Stock
Reconciliation, Demand & Recovery, Final Integrated Report) but is explicit that only
**Module 01 — Import Audit** is in scope now, with the rest built "later ... to the same
platform." Acceptance criteria (§26) define what "done" means for v1. Everything in this
build targets those criteria; the future modules only influence naming and the
integration contract (§27) so they can be added without reshaping M01.

## 2. Technology choices

| Layer | Spec recommendation | Chosen | Why |
|---|---|---|---|
| Frontend | Next.js + TypeScript, Tailwind + shadcn/ui | Same | As specified. |
| Backend | FastAPI (Python) | Same | As specified. |
| Database | PostgreSQL (Supabase Postgres recommended) | SQLAlchemy models targeting PostgreSQL, driven by `DATABASE_URL` | No Supabase project/credentials exist for this environment. The schema, migrations and queries are plain PostgreSQL (via `psycopg`), so pointing `DATABASE_URL` at a Supabase Postgres instance is a config change, not a rewrite. Local dev/CI uses either a real Postgres (docker-compose) or SQLite for fast unit tests — SQLite is test-only, never the target for money/Decimal-sensitive migrations. |
| Storage | Supabase Storage or S3-compatible | `StorageBackend` interface with a local-filesystem implementation now, S3-compatible (`boto3`) implementation included behind the same interface | Same reasoning as the database: no object-storage credentials are available here. Evidence files are content-hashed and written as immutable, so swapping the backend later doesn't change the evidence model. |
| Auth | Supabase Auth | Self-contained JWT auth (passlib + python-jose) with the same 4-role model (§20) | No Supabase Auth project is reachable from this sandbox. Auth is isolated behind `app/core/security.py` and `api/deps.py`; swapping to Supabase Auth later means replacing token verification, not the RBAC model, which is already enforced per-endpoint. |
| Excel processing | Python + pandas + openpyxl | Same | As specified. |
| AI assistance | Optional Claude API layer, suggestions only | Deterministic similarity scoring (RapidFuzz-style normalized string match) stands in for the optional Claude API call, behind a single `suggest_match()` seam | The spec is explicit that AI must never make a final match/audit decision (§10, §24) — matches always require `AuditorConfirmation`. Because AI is explicitly a *suggestion* source and optional, a real Claude API integration can be dropped into that seam later (e.g. calling Claude for ambiguous material-name matches) without touching the approval workflow, which is unaffected either way. |

**Network constraint that shaped this plan:** this sandbox's egress policy allows GitHub
but blocks `pypi.org` and `registry.npmjs.org` (confirmed via direct requests — both
return "Host not in allowlist"). `pip install` / `npm install` cannot run here, so
dependencies could not be installed or executed locally in this session. To compensate:
`.github/workflows/ci.yml` installs and runs the full backend pytest suite and the
frontend build/typecheck on GitHub's runners (which do have registry access) on every
push; this is a working substitute for the "run tests" step. Locally, `python3 -m
py_compile` was run over every backend module and `tsc --noEmit` (already present as a
global tool in this image) was run over the frontend to catch syntax errors before
committing.

## 3. Monorepo layout

```
backend/            FastAPI service — the audit engine
  app/
    core/            settings, security/JWT, db session, RBAC permission matrix
    db/               declarative Base
    models/           SQLAlchemy ORM models (one module per aggregate)
    schemas/          Pydantic request/response schemas
    services/         business logic engines (no FastAPI imports — testable in isolation)
    api/routers/      thin HTTP layer that calls services
  alembic/            migrations (0001 initial schema)
  tests/              pytest, one file per engine + workflow integration test
frontend/            Next.js App Router application
  app/                routes, following the 17-step workflow in spec §22
  components/ui/      hand-authored shadcn-style primitives (no shadcn CLI network call)
  components/          feature components per module
  lib/                 typed API client, auth context, shared types
docs/                 this file, plus data-model and API notes
docker-compose.yml    local Postgres + backend + frontend for development
.github/workflows/    CI
```

Two hard rules drove this split:

- **Services never import FastAPI.** Every audit engine (classification, matching,
  conversion, excess, duty, reporting) is a plain Python module operating on
  dataclasses/ORM objects and returning results. Routers are a thin translation layer.
  This is what makes "every calculated result must be reproducible" (§24) and unit-tested
  in isolation possible, and it's what a future Consumption/Export module reuses.
- **Nothing computed is trusted without evidence.** Every conversion, match and duty
  figure carries a `source_evidence` / `*_evidence` string back to the originating
  document + row. This isn't a nice-to-have, it's the mechanism behind §19 (audit trail)
  and §24 (traceability) — the schema makes "unsourced number" structurally awkward to
  produce.

## 4. Three-layer evidence model (§5) mapped to storage

- **Layer A — Raw Evidence**: uploaded files land in `source_documents` (checksum,
  original filename, uploader, timestamp) and are written byte-for-byte to storage.
  Parsed raw rows are kept in a `raw_row_number`/`raw_payload` (JSON) column alongside
  every downstream table — the original spreadsheet row is always one lookup away, and
  raw values are appended to, never edited in place.
- **Layer B — Normalized Data**: `import_transactions`, `bill_of_entries`,
  `duty_components` hold the typed, normalized working records (Decimal quantities,
  string HS codes, normalized dates/currencies), each with a foreign key back to its
  Layer A row.
- **Layer C — Audit Results**: `entitlement_items` matches, `classification` +
  `classification_confidence`, `review_status`, excess flags, and the `findings` table
  are all derived, recomputable outputs — never hand-edited; changes go through the
  matching/review workflow so they're captured in `audit_log`.

## 5. Data model

See `docs/DATA_MODEL.md` for the full column-level schema. It implements §7–9 verbatim
(entitlement_groups/items, import_transactions, bill_of_entries/duty_components) plus the
supporting tables the spec implies but doesn't enumerate: `companies`, `audits`, `users`,
`source_documents`, `column_mapping_templates`, `findings`, `audit_log`.

Monetary and quantity fields are `NUMERIC` (Python `Decimal`), never `FLOAT` (§24). HS
codes are `VARCHAR`, never numeric, to preserve leading zeros (§24).

## 6. Rule engines — implementation notes

- **Classification (§15)**: keyword/HS-chapter heuristics with a confidence score;
  anything below threshold is `Unknown` and forced into the review queue rather than
  guessed (§3: "flag ... rather than guessing").
- **Matching (§10)**: strict pipeline — exact HS → normalized name → similarity
  suggestion → auditor confirmation. Only `AuditorConfirmation` can set a match's status
  to `APPROVED`; an AI suggestion alone can only reach `SUGGESTED`, never `APPROVED`.
- **Conversion (§11–12)**: refuses to invent a factor. If a transaction has no B/E
  conversion evidence, its entitlement-unit/KG/USD fields stay null and it's flagged
  `REVIEW_REQUIRED` instead of silently defaulting.
- **Excess detection (§14)**: processes each entitlement item's transactions in
  chronological B/E order, carrying a running cumulative total; a single B/E that
  straddles the entitlement ceiling is split into an allowed portion and an excess
  portion (the worked example in §14 — 10,000 approved / 9,500 prior / 1,000 current →
  500 allowed / 500 excess — is a literal unit test).
- **Duty/demand (§9)**: sums `duty_components` per Bill of Entry using `Decimal`
  arithmetic only, and only over the excess/non-entitled quantity portion identified by
  the engines above — never the full transaction.
- **Reporting (§16–18)**: Outputs 01–07 are generated from Layer C data by
  `services/reporting_engine.py` using openpyxl, preserving entitlement sequence (never
  alphabetically sorted, §17) with group subtotals and grand totals. The Bijoy/SutonnyMJ
  transformation (§18) is isolated to the export layer as a single conversion function so
  the database only ever stores Unicode.

## 7. Sequencing

Implementation follows the spec's own §23 phase list 1→9, each phase landing as a
reviewable, independently testable slice rather than one big drop, per §25's
instruction to "implement the smallest complete vertical slice" at a time. Frontend
screens are added once the backend slice they depend on exists, following the workflow
order in §22.
