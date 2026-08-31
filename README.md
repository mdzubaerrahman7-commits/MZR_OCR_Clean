# BondAudit Platform — Import Audit Module 01

An enterprise Customs Bond Import Audit application, built from
`Claude-Ready Master Development Specification — Enterprise Customs Bond Import Audit
System v1.0`. This module (Import Audit) ingests Import MIS and entitlement Excel
files, classifies and matches imports against approved entitlement, detects
non-entitled and excess imports chronologically, assesses potential duty/demand, and
generates the seven required audit outputs — all with an evidence trail back to the
original spreadsheet rows.

See `docs/ARCHITECTURE.md` for the full design rationale and `docs/DATA_MODEL.md` for
the schema. This repository also still holds the original document-repository content
(`Consumption_Report_Jan2025_OCR_and_Legal_References.md` and its source image) that
predates this application — see the bottom of this file.

## Stack

- **Backend**: FastAPI (Python 3.11), SQLAlchemy 2.0, Alembic, pandas + openpyxl for
  spreadsheet parsing, PostgreSQL in every real environment (SQLite only for fast unit
  tests).
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS. Installable as a PWA
  on desktop and mobile — see "Installing as an app" below.
- **Auth**: self-contained JWT auth with the 4-role model from the spec
  (Administrator / Auditor / Reviewer / Viewer) — see "Known gaps" below for why this
  isn't Supabase Auth yet.

## Repository layout

```
backend/     FastAPI service — models, services (the audit engines), API routers, tests
frontend/    Next.js application
docs/        Architecture, data model
docker-compose.yml   Postgres + backend + frontend for local development
.github/workflows/ci.yml   Backend pytest + frontend build/typecheck
```

## Running locally

### With Docker (recommended)

```
docker compose up --build
```

Backend on http://localhost:8000 (docs at `/docs`), frontend on http://localhost:3000.
The backend runs `alembic upgrade head` on startup.

First run: open the frontend, use "First time setting this up? Create the admin
account" on the login page to bootstrap an Administrator (this path only works while
zero users exist).

## Installing as an app (PWA)

The frontend is an installable Progressive Web App — same codebase, no separate
mobile build:

- **Desktop (Chrome/Edge)**: an install icon appears in the address bar; or use the
  browser menu → "Install BondAudit…". It opens in its own window, pinned to the
  taskbar/dock/Start menu like a native app.
- **Android (Chrome)**: browser menu → "Add to Home screen" / "Install app".
- **iOS/iPadOS (Safari)**: Share button → "Add to Home Screen". (Safari doesn't show
  Chrome's install prompt, but the app still launches full-screen from the home
  screen icon.)

Installability requires HTTPS in production (a plain `localhost` dev server is
exempted by browsers for testing). The service worker (`frontend/public/sw.js`) is
intentionally minimal — it only makes the app installable and shows a friendly
offline page if the connection drops mid-navigation. It never caches API responses,
JS/CSS bundles, or auth tokens, so it can't ever serve a stale duty/demand figure or a
stale build: every audit engine call and every asset always goes to the network.

### Without Docker

Backend:

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # point DATABASE_URL at your own Postgres, or leave the SQLite default for a quick try
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

### Tests

```
cd backend
pytest -v
```

## Main workflow (spec section 22)

Create Company → Create Audit → Upload Entitlement Sheet → Upload Import MIS → Review
Column Mapping → Parse (filters to the audit period automatically) → Classify → Build
Entitlement Master → Match Raw Materials to Entitlement → Enter Bill of Entry evidence
→ Calculate Conversions → Detect Excess (this also flags non-entitled imports) →
Review Exceptions → Generate/Approve Findings → Generate Excel Outputs 01–07 → Lock /
Archive the audit. The frontend's per-audit tabs follow this order.

## Known gaps / things a real deployment must change

This was built in a sandboxed session with **no access to PyPI or the npm
registry** (confirmed via direct requests — both returned "host not in
allowlist"), so nothing here could be `pip install`ed / `npm install`ed or executed
locally. Every file was validated with `python3 -m py_compile` (backend) and the
TypeScript compiler in isolation (frontend, ignoring "cannot find module" errors from
the absent `node_modules`) — real execution happens for the first time in
`.github/workflows/ci.yml`, which is why driving that workflow green is the immediate
next step after this lands, and why some of the following need attention in an
environment with real package/service access:

- **Database**: defaults to a local SQLite file so the app can boot without any
  infrastructure. Point `DATABASE_URL` at a real PostgreSQL (Supabase Postgres per the
  spec's recommendation) for anything beyond a quick look.
- **Storage**: defaults to local-filesystem evidence storage. `STORAGE_BACKEND=s3`
  switches to the S3-compatible backend (works against Supabase Storage), but needs
  real bucket credentials.
- **Auth**: self-contained JWT rather than Supabase Auth (no Supabase project exists
  here to wire up) — see `docs/ARCHITECTURE.md` section 2 for the swap plan.
- **Frontend dependencies have never been installed**: there is no committed
  `package-lock.json` yet. The first `npm install` run with real registry access
  should commit the resulting lockfile.
- **Bijoy/SutonnyMJ export** (`backend/app/services/bijoy_export.py`): implements the
  structural conversion rules but is explicitly a first pass — the spec itself
  requires validating this against real Bijoy/SutonnyMJ rendering before production
  use, and that hasn't happened yet.
- **Duty proration**: `backend/app/services/duty_engine.py` prorates a Bill of Entry's
  auditor-entered total duty by quantity ratio rather than modeling a specific
  cascading tax formula (CD → RD → SD → VAT → AIT...), since the spec doesn't specify
  one. If a real cascade is required, this is the module to extend.

## Original document-repository content

Before this application existed, this repository held a single OCR transcription
task: `1Consumption January 2025_260625_221322_7.jpg` (a scanned bonded-warehouse
Consumption Report) and `Consumption_Report_Jan2025_OCR_and_Legal_References.md` (its
transcription plus a Bangla note on applicable customs/VAT/EPZ law). Both remain in
the repository root, unrelated to the application above.
