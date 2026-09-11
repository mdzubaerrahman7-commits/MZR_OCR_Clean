# BONDAUDIT — EXISTING SYSTEM TECHNICAL AUDIT & GAP ANALYSIS

**Phase:** 1 (audit only — no code, schema, or data was changed to produce this report)
**Audited artifact:** `app.tar.gz` (Convex + React/Vite source, tagged **v74**, frozen 2026‑09‑11) + Convex database snapshot `snapshot_1789155238740513423.zip`
**Method:** Every claim below was checked against the actual source (schema.ts, all `convex/*.ts`, `src/lib/**`, `src/pages/**`), not against the bundled `MIGRATION/*.md` docs. Where those docs are right, that's stated; where they're wrong, incomplete, or contradicted by the code, that's stated explicitly with file:line evidence. Legal citations were spot-checked against nbr.gov.bd where feasible; anything not independently confirmable is marked **VERIFY REQUIRED**, not asserted.

---

## A. Executive Summary

BondAudit-on-Convex is a **real, feature-complete-on-paper, single-tenant pilot system**, not a prototype and not production-hardened. It covers the full bond-audit lifecycle — entitlement → import → 5-level matching → excess detection → duty assessment → bond register/closing stock → VA → তফসিল-৪ wastage → findings → Word/Excel reporting — plus two GPT-based Bengali/English advisory agents. The database snapshot shows genuine pilot use (2 real named users, 3 real companies, 3 real audits, real uploaded files) but **every downstream table is still empty** — no audit in the snapshot has been carried past document upload. The system has never been exercised end-to-end on real data.

Five findings dominate the risk picture:

1. **RBAC is not enforced.** The 4-role permission matrix in `convex/lib/rbac.ts` is dead code outside `users.ts`. Every core write engine (excess detection, duty assessment, findings, schedules, bond register, VA) only checks "is logged in," not "is this role allowed." Three of `schedules.ts`'s mutations (`updateRow`, `clearSchedule`, `deleteRow`) have **no auth check at all** — an unauthenticated client can wipe schedule data outright. No mutating engine checks the audit's `locked` status. (§L)
2. **A live, structural VA% mismatch exists today**, not as a risk but as a fact: the VA Calculator tab shows an unweighted average of per-record VA%, the Word report independently recomputes a value-weighted average from the same rows. They disagree whenever export values are unequal — which is the normal case. (§I, §N)
3. **`potentialDutyDemand` vs `dutyDemand`** is a real blind spot, not just staleness: a finding populated only via the Duty Rate Registry path shows **zero duty demand** in the legal Word/Excel report, because the report reads only `potentialDutyDemand`. The bundled docs even misattribute which function writes which field — independent verification caught this. (§I, §N)
4. **A fully-built 13-test audit engine (T‑01…T‑13, ~112 KB, includes a genuine BBLC 3-way triangulation) is completely disconnected from the running app** — zero imports from any page or Convex function. The docs claim 6 of these tests are "not implemented"; they exist, they're just orphaned. (§F/G/H, §O)
5. **Test coverage is close to zero where it matters most**: 0% of ~34,000 lines of frontend TypeScript, ~7% of Convex backend files, and the one existing duty-cascade test suite hardcodes the AT rate to 0 in every case — so it never exercises the one formula known to be inconsistent in the AI's own prompt text. (§I, §M)

Separately: this same git repository **already contains a second, independent BondAudit implementation** (FastAPI + Next.js + Postgres, under `backend/`/`frontend/`), built to a different master spec and scoped to only "Module 01 — Import Audit." It is real (4,536 backend lines, 2,338 frontend lines, 1,485 lines across 18 test files, 21 commits) but has no bond register, closing stock, VA, or schedule tracking at all, and was never executed end-to-end (its own CI is the only place its tests have ever run). The two systems are unrelated in code and stack but overlapping in purpose — see §B and §P for what to do about that.

None of this means "rewrite it." The calculation cores — duty cascade, bond-register reconciliation, matcher thresholds, schedule‑4 wastage — are correct, internally consistent within each engine, and match the legal constants the system claims. The problems are almost entirely at the *boundaries*: authorization, cross-engine consistency, test coverage, and one orphaned subsystem. See §O for what to leave alone.

---

## B. Current Architecture

Two unrelated, independently-built BondAudit systems exist across the material reviewed for this audit:

| | **BondAudit‑Convex** (this audit's primary subject) | **BondAudit‑FastAPI** (already in this git repo, `backend/`+`frontend/`) |
|---|---|---|
| Stack | Convex (BaaS) + React 19/Vite 8 SPA, TypeScript throughout | FastAPI (Python) + SQLAlchemy/PostgreSQL + Next.js App Router |
| Scope | Full lifecycle: entitlement, import, matching, excess, duty, bond register, closing stock, VA, তফসিল‑৪, findings, Word/Excel reports, 2 AI agents | Only "Module 01 — Import Audit": classification, matching, conversion, excess, duty apportionment, reporting (7 Excel outputs incl. Bijoy font export) |
| AI role | Two GPT agents (advisory + tool-calling); calculation itself is deterministic Convex code | Deterministic similarity scoring stands in for an *optional* future Claude call; spec explicitly forbids AI from finalizing a match (§10/§24 of its spec) |
| Evidence model | Implicit — no formal "never persist a number without its source row" layer | Explicit 3-layer evidence model (Raw → Normalized → Audit Results); refuses to invent conversion factors, flags `REVIEW_REQUIRED` instead |
| Maturity signal | Real pilot data exists (3 companies/3 audits) but none progressed past document upload | 21 commits over ~6 weeks, real CI (GitHub-hosted, since local sandbox blocked `pypi`/`npm`), never run end-to-end even once |
| Auth/RBAC | 4-role matrix defined, **not enforced** in most engines (§L) | RBAC enforced per-endpoint per its own docs; not independently verified in this audit (out of scope — see note below) |

Recommendation is deferred to §P, but the short version: these are not "two drafts of the same app" — they differ in scope, stack, and philosophy (evidence-first vs. feature-first). Don't merge their code; decide which one the organization is actually going to run, and treat the other as either archived reference or a for-later "Module 02+" donor of its evidence-model discipline. This audit's line-by-line verification effort went almost entirely into BondAudit‑Convex, since that is the system with real pilot data and the fuller feature set; the FastAPI system's characterization above comes from a structural review (file counts, test presence, spec-conformance) rather than the same statement-by-statement checking applied below — treat its "RBAC enforced" claim as unverified by this audit, not confirmed.

**BondAudit‑Convex tech stack** (`package.json`, confirmed exact): React 19.2.8, Vite 8.2.1, TypeScript 6.0.3, Tailwind 4.3.3, Convex 1.43.0, openai SDK 7.8.0 (pointed at a third-party "Hercules AI Gateway," not OpenAI directly), docx 9.7.1, xlsx (SheetJS) 0.18.5, react-router-dom 7.18.2, Vitest 4.1.10. Two Node.js-runtime files (`convex/agent/chat.ts`, `convex/freeChat/chat.ts`) hold the OpenAI calls; everything else runs in Convex's V8 runtime. No HTTP actions/webhooks exist — all data entry is through the UI or the AI agent's tools.

---

## C. Database Architecture

`convex/schema.ts` defines **28 tables** (not 24 — an old figure the docs themselves already correct). Verified directly, table-by-table, against the schema source; the MIGRATION doc's schema description (`02-database-schema.md`) is **accurate** on structure, field names, validators, and indexes — this is one area where the bundled docs hold up well under verification.

Two structural facts worth flagging on their own:

- **`audits.scheduleType`** (exporter category: schedule_1…schedule_5) and **`schedule_records.scheduleType`** (which তফসিল ছক a row belongs to, including `schedule_3a`/`3b`/`rmg_ud`/`rmg_consumption`) are two *different enums sharing one field name across two tables*. A query author unfamiliar with this will write a subtly wrong filter. Confirmed real (schema.ts:39-45 vs. schema.ts:521-530); already flagged in the bundled docs, and worth fixing regardless of who flagged it first.
- **Schedule‑4 is normalized** (`schedule4_rows`, typed columns, server-computed `approvedQty`/`variance`/etc.) while **every other schedule (1, 2, 3a, 3b, 5, rmg_ud, rmg_consumption) is a JSON blob** in `schedule_records.rowData: v.string()`, with column *definitions* living only in code (`SCHEDULE_COLUMNS` in `convex/schedules.ts`). This isn't a bug, but it means every schedule except Schedule‑4 is unqueryable by column value without parsing JSON in application code, and has no server-side type safety.

**Data reality (from the snapshot, not from the schema):** 2 real named users, 3 real companies (Tiyani Outdoor, M&M Travelling Goods, Stella Hair Products), 3 real audits, a handful of uploaded source documents with real column-mapping JSON. **All 20 other tables are empty** — `entitlement_items`, `import_transactions`, `bill_of_entries`, `audit_findings`, `bond_register`, `schedule_records`, `duty_rate_registry`, `va_records`, `schedule4_rows`, `agent_messages`, `training_examples`, everything. This is not synthetic seed/demo data and not a fabricated example set — it is a real, if very early, pilot that has only ever reached the "upload + confirm column mapping" step of the documented 10-step workflow. Do not read "28 tables, rich schema" as evidence the calculation pipeline has ever produced a real number in production.

---

## D. AI/Agent Architecture

Two agents, exactly as the docs claim structurally, both calling an OpenAI-compatible endpoint (`https://ai-gateway.hercules.app/v1`, model default `openai/gpt-5.6-sol`, `temperature: 0.1`, `max_tokens: 2000` — identical params, both agents):

| | Audit Agent (`convex/agent/chat.ts`) | Dashboard Free Chat (`convex/freeChat/chat.ts`) |
|---|---|---|
| Tools | **20**, not 17 and not 19 (see below) | 0 |
| Data access | Full audit context via tools | None |
| History window | last 28 messages | last 20 messages |
| Memory | `agent_memory` table, injected as text | none |
| Loop | up to 5 tool-calling iterations | single shot |

**Tool count — corrected.** The bundled docs went 17→19 across two revisions. Actual count, verified by grepping every `name:` field inside the `AGENT_TOOLS` array (`chat.ts:532-815`): **20 tools are registered and callable by the model.** In addition, the `executeTool` switch statement (`chat.ts:819-1182`) contains a **21st case, `get_schedule4_data` (chat.ts:1150-1175), that has no matching entry in `AGENT_TOOLS`** — fully implemented, completely unreachable, because the model is never told this tool exists. This is dead code left over from development, not a functioning feature. Neither prior count (17 or 19) was correct; the number that matters — what the model can actually call — is 20.

**System prompt.** `SYSTEM_PROMPT` (chat.ts:23-520, ~498 lines) was read in full, not sampled. It is structurally as the docs describe: identity, workflow manual, proactive-warning rules, an extensive legal-citation table (Customs Act 2023, Warehouse Licensing Rules 2024, EPZ rules, Import/Export Policy Orders, VAT/SD Act, AIT, BEPZA, SRO 209-214, SRO 284/2025 amendment), an explicit anti-hallucination section ("say 'I don't know reliably' rather than guess a rate/date/SRO number"), and a deep-citation table for show-cause notices. One internal inconsistency, confirmed in the code itself: line 371 states `AT = AV × at_rate%`, but the later "T‑09" section at line 501 states `AT = (AV+CD+RD+SD) × at%` — two different bases for the same tax component, ~130 lines apart in the same prompt. **This is prompt-text-only**: the actual `calculate_duty` tool (chat.ts:884-893) and every backend calculation file (`dutyAssessment.ts`, `dutyRateRegistry.ts`) consistently use the AV-only base, so no persisted number is affected. But if a user asks the agent to *explain* the AT calculation rather than invoking the tool, the model has two contradictory instructions to draw from — a real, if contained, hallucination vector. Fix is a one-line prompt edit, not a code change.

**Legal citation spot-check.** SRO ২১২-আইন/২০২৪/৬৪ and SRO ২১৩-আইন/২০২৪/৬৫ were confirmed to exist on nbr.gov.bd with titles matching the app's description (Non‑RMG vs. RMG temporary‑importation/bond rules respectively). The 2025 amendment, SRO ২৮৪-আইন/২০২৫/৫৬, could not be independently confirmed via web search in the time available — mark **VERIFY REQUIRED**, the same posture this repository's *own* OCR legal-reference document already takes toward one of its citations. A full ধারা-by-ধারা, বিধি-by-বিধি accuracy review is outside what source-code inspection can establish and needs a qualified customs professional against the primary SRO PDFs.

**Token cost, quantified.** `convex/lib/masterKnowledgeBase.ts` + `convex/lib/sroKnowledgeBase.ts` together are **129,499 characters** (~32,000+ tokens at a 4-char/token rule of thumb), sent in full, on *every single call, from both agents, regardless of what was asked*. Add the ~498-line system prompt (~6,000+ tokens) and up to 28 messages of history, and a simple "what document do I need?" question costs on the order of **35,000+ input tokens before the user's own message is counted** — and that cost repeats on every iteration of the up-to-5-iteration tool loop, since each iteration resends the full message array. There is no RAG/embedding retrieval anywhere (confirmed: no vector store, no chunking, all knowledge is TypeScript string constants) — so a Non‑RMG audit gets the full RMG (SRO 213) knowledge dump and vice versa. See §M and §S.

**Where the AI is allowed to write, unchecked.** `fill_schedule` and `fill_schedule4` let the model persist structured audit-record rows (schedule contents, তফসিল-৪ coefficients/quantities) directly via `bulkAddRows`/`schedule4.bulkAddRows`. A separate `validate_schedule` tool exists to cross-check math, but nothing *forces* the model to call it before or after a fill — it's the model's discretion. This is the one place in the architecture where "AI should not be the final source of truth" (the stated target principle) is structurally at risk: a hallucinated coefficient or quantity can become a persisted schedule row with no synchronous deterministic gate. `calculate_duty`, by contrast, is the right pattern — the model is *forced* through a deterministic function rather than doing arithmetic itself — and should be the template for tightening `fill_schedule`/`fill_schedule4`.

**Traceability gap.** `convex/auditTrail.ts` is query-only; the actual `insert("audit_trail", …)` calls live in 9 files (`audits.ts`, `dutyAssessment.ts`, `dutyRateRegistry.ts`, `entitlements.ts`, `excessDetection.ts`, `findings.ts`, `imports.ts`, `matching.ts`, `notes.ts`). **`convex/agent/chat.ts` is not among them** — no AI-driven `fill_schedule`, `fill_schedule4`, or `save_memory` call ever writes an `audit_trail` entry. The only record of an AI write is the raw tool-call JSON inside `agent_messages`, which is not surfaced in the Audit Trail tab a reviewer would actually look at. `schedules.ts`, `schedule4.ts`, `bondRegister.ts`, `bondRegistrar.ts`, `checklist.ts`, `udUp.ts`, `docRequests.ts`, `schedule3b.ts`, and `vaCalculator.ts` are also absent from the audit-trail writers — meaning several human-driven decision points (locking a bond-register variance, marking a checklist result, adjusting VA) leave no old-value/new-value/reason trail either, despite that being exactly what the audit-trail table exists for.

---

## E. Existing Features (full inventory)

Everything below exists as real, non-stub code, verified by direct reading, not by trusting a doc table: company CRUD; audit lifecycle incl. lock/unlock; document upload + column mapping (60+ Bangla/English synonym dictionary); entitlement register (bulk import, enhanced entitlement); import MIS bulk import + classification; 5-level HS/name matcher; excess/non-entitled detection; duty assessment (B/E-based) *and* a separate duty-rate-registry-based assessment path; findings register with review workflow; bond register reconciliation; বন্ড রেজিস্ট্রার (তফসিল‑১) auto-populate + into-bond gap detection + demand-note drafting; bond-register-based closing stock with 730-day staleness; তফসিল‑৩(খ) VA analysis; তফসিল‑৪ wastage with auto-computed variance; generic schedule management for the remaining তফসিল types; UD/UP/EP tracker; SRO-213-style audit checklist; document-request tracker; audit trail viewer; notes; Word report (~2,900 lines, 7 sections); 3 Excel report builders; RBAC data model (not enforced — §L); Hercules OIDC auth; admin panel; push notifications; PWA shell; a **second, fully-implemented but completely disconnected** 13-test audit engine (§O); a self-learning/training-example pipeline with 15-day cron reports.

## F. Implemented Features (verified end-to-end, reachable by a real user)

Company/audit CRUD, document upload+mapping, entitlement/import bulk import, the 5-level matcher, excess detection, duty assessment (both paths), findings CRUD/review, bond register + closing stock + বন্ড রেজিস্ট্রার তফসিল‑১, তফসিল‑৩(খ) VA analysis, তফসিল‑৪ wastage, generic schedule fill/validate (human or AI-driven), UD/UP/EP tracker, checklist, doc requests, notes, Word/Excel report generation, RBAC data model + admin role management (the *matrix* isn't enforced downstream — the admin screen itself works), auth, push notifications, PWA shell (with real limitations, §I), both AI agents. This list is functionally reachable through the UI — "implemented" here means "a user can click to it and it runs," not "runs correctly in every case" (see §I/§N for where the numbers can disagree).

## G. Partial Features

- তফসিল‑৩(ক) and তফসিল‑৫: column definitions exist in `SCHEDULE_COLUMNS`, no dedicated tab/auto-population — usable only through the generic SchedulesTab or the AI agent's `fill_schedule`.
- RMG UD/consumption schedules (`rmg_ud`, `rmg_consumption`): schema + `SCHEDULE_COLUMNS` exist, no dedicated UI.
- EPZ UP→EP column relabeling: the agent's system prompt knows the rule; no code-level UI switch exists — an EPZ audit will still show "UP" labels.
- Bulk operations: classification, entitlement-item edit, and match confirmation are all one-at-a-time only; the corresponding bulk dialogs don't exist.
- Training-example export (`exportAll`): produces JSONL, nothing consumes it — infrastructure without a pipeline (§T).

## H. Missing / Orphaned Features — corrected from the bundled docs

The bundled `08-feature-status.md` lists T‑07 (BBLC 3-way match), T‑08 (export proceeds ageing), T‑10 (machinery/capital compliance), T‑11 (financial solvency), T‑12 (VDS reconciliation), and T‑13 (zero-rated docs review) as **"Not Implemented … no backend function."** This is **wrong, verified by direct code inspection**: `src/lib/audit-engine/test-t07.ts` through `test-t13.ts` all exist, all contain real logic (T‑07 alone is a 159-line three-way LC-source triangulation with severity grading), and all are registered in `src/lib/audit-engine/runner.ts`'s `TEST_REGISTRY`. What's actually true, and what the docs miss entirely: **the whole `src/lib/audit-engine/` module — all 14 tests (T‑01…T‑13 plus T‑04A), the runner, and its public API — is never imported by any page component or any Convex function.** `grep -r "audit-engine"` across `src/pages/` and all of `convex/` returns nothing outside the module's own files. It is complete, internally wired to itself, and 100% unreachable by any user action or AI tool. The docs' own "Complete" list includes "Client-side audit engine (13 tests)" — technically true and functionally misleading, since nothing in the running app can trigger it.

Genuinely missing (not orphaned, just absent): entitlement-ceiling T‑04A UI (the calc exists in the orphaned engine only), inter-bond transfer tracking, DTA sale audit, sub-contracting traceability, anti-dumping duty handling, and a working exchange-rate lookup (the "Bangladesh Bank rate of the B/E date" the agent's prompt promises does not exist anywhere in code — see §I).

---

## I. Bugs & Critical Risks

Ranked by real-world consequence, each independently verified against source:

1. **Unauthenticated writes on `convex/schedules.ts`.** `updateRow` (line 318), `clearSchedule` (line 341), and `deleteRow` (line 363) contain **no auth check of any kind** — not role, not even `ctx.auth.getUserIdentity()`. Sibling mutations `addRow`/`bulkAddRows` in the same file *do* check authentication. Any client holding the Convex deployment URL can call `clearSchedule` and delete an entire তফসিল's rows for any `auditId`, logged in or not. **P0.**
2. **Live VA% mismatch between the VA Calculator tab and the Word report.** `vaCalculator.ts:getSummary` (lines 177-178) computes an unweighted mean of per-record `vaPct`; `word-report-builder.ts` (lines 2026-2029, 1226, 2330) independently recomputes a value-weighted VA% from the same `va_records` rows. These are different statistics and will disagree whenever export FOB values differ across records — the normal case, not an edge case. **P0.**
3. **`potentialDutyDemand` vs `dutyDemand`: a finding can show ৳0 duty in the legal deliverable while a nonzero figure sits in the Duty Rate Registry.** `dutyAssessment.runDutyAssessment` writes `potentialDutyDemand`; the separate `dutyRateRegistry.applyRatesToFindings` writes `dutyDemand` on the same row from a different rate source. Every consumer that matters — `word-report-builder.ts`, `findings-excel-builder.ts`, `ReportsTab.tsx`, `FindingsTab.tsx` — reads **only** `potentialDutyDemand`. If an auditor uses the Duty Rate Registry workflow without also running `runDutyAssessment`, the exported report is silently wrong, not just stale. (The bundled `09-known-bugs...md` also misattributes `potentialDutyDemand`'s writer to `excessDetection.runDetection` — it's actually `dutyAssessment.ts` — a concrete example of why source code, not docs, has to be the reference.) **P0.**
4. **Third VA formula disagrees on the pass/fail line itself.** The orphaned audit-engine's `test-t06.ts` (via `assessment-formulas.ts:checkValueAddition`) computes VA% against the *imported-input value* as denominator, not FOB — the opposite of `vaCalculator.ts` and `schedule3b.ts`. Near the 15% threshold this can flip pass/fail for identical underlying figures. Currently dormant only because the audit-engine is unreachable (§H) — but it is what a developer will copy from if anyone ever wires that engine up. **P1 today, P0 the moment T‑06 is connected to anything.**
5. **Hardcoded exchange rate (১১০ টাকা/USD) is used in a real, persisted calculation**, not just prompt text: `convex/schedule3b.ts:66` defaults `exchangeRate` to 110 and feeds it into `shortfallBdt`/`vatOnShortfallBdt` on a finding; the frontend independently hardcodes the same default in `Schedule3bTab.tsx:65`. Two places to remember to change, and no B/E-date-based lookup exists anywhere despite the agent's own prompt promising one. **P1.**
6. **RBAC matrix is unenforced almost everywhere that matters** — detailed in §L; listed here because it is also a data-integrity bug: a "viewer" account can call `runDetection`, `runDutyAssessment`, `applyRatesToFindings`, `bulkAddRows`, `upsertRecord` (VA), and every `findings.ts` mutation, because these engines check only `requireUser` (authenticated) or a locally-duplicated `requireAuditAccess` that skips role/ownership entirely. **P0.**
7. **No mutating engine checks the audit's `locked` status** except `audits.ts` itself (`lockAudit`/`unlockAudit`). A "locked" (finalized) audit can still be silently re-mutated by excess detection, duty assessment, findings, schedules, bond register, and VA calculators. **P0.**
8. **Service worker registers `push` and `notificationclick` listeners twice** (`public/sw.js`, near-duplicate blocks). Service workers fire every registered listener per event — this double-fires notification display/focus logic on every push, a real functional bug, not cosmetic. **P2.**
9. **Two different Excel header-scan limits in two different parsers**: `excel-parser.ts` scans 30 rows, `import-mis-parser.ts` scans 20 then 15 in a fallback pass — inconsistent, and both parsers claim (in comments) to handle merged header cells while neither actually processes SheetJS's `!merges` metadata. **P2.**
10. **Date parsing has no format validation or auto-detection**: `import-mis-parser.ts` tries a `DD/MM/YYYY` regex unconditionally with no month-range check, so a `MM/DD/YYYY`-formatted date like `12/25/2024` is silently misparsed. **P1** for any Import MIS export that isn't strictly DD/MM.
11. **Test suite hardcodes the one at-risk value to zero.** Every `atRate` in `dutyAssessment.test.ts` is `0` — the test suite structurally cannot detect a regression in the AT formula, the exact spot where the AI's own prompt text disagrees with itself (§D). **P1.**

---

## J. Legal / Calculation Risks

- **Confirmed consistent in code** (four independent implementations agree): the NBR duty cascade `CD=AV×cd%, RD=AV×rd%, SD=(AV+CD+RD)×sd%, VAT=(AV+CD+RD+SD)×vat%, AT=AV×at%, AIT=AV×ait%` — in `dutyAssessment.ts`, `dutyRateRegistry.ts`, the agent's `calculate_duty` tool, and `src/lib/knowledge/audit-procedures.ts`'s `computeCascadeTax`. The only place this formula is stated differently is prompt text (§D, §I‑#4/finding numbering above refers to VA, this AT note is the D-section prompt inconsistency) — **no persisted number is affected today.**
- **VA% has three live/dormant definitions** with a real pass/fail-flipping disagreement — §I‑#2 and §I‑#4. Needs one canonical formula decided and every consumer (tab, report, orphaned test) pointed at it.
- **Legal citation framework verified to exist**: SRO 212 and 213 (2024) confirmed against nbr.gov.bd. **VERIFY REQUIRED**: SRO 284/2025 amendment details, and all sub-clause-level ধারা/বিধি numbers and rates cited throughout the knowledge base and system prompt — this audit checked top-level SRO identifiers, not every citation, and that finer-grained check needs a customs-law professional against primary texts, per the platform's own stated standard.
- **Exchange rate**: §I‑#5. Any duty/VA figure computed through `schedule3b.ts` without an explicit auditor-entered rate silently uses ৳110/USD.
- **Storage-period / stale-stock threshold (730 days)** and **bond-register variance thresholds (0.5%/2%)** were verified exactly as coded and match the documented legal basis (SRO 211, ধারা ১২৬(গ)) — no issue found.

## K. Data Integrity Risks

- The `computeClosingStock()` duplication between `convex/reports.ts` (lines 397-492) and `convex/closingStock.ts` (lines 75-218) currently produces **identical values** (only a display sort-order differs) — a lower-severity finding than initially expected, but still two hand-maintained copies of ~90 lines of aggregation logic that will silently diverge the next time either is edited without the other.
- Duty cascade is independently implemented in **four** files (§J) — all agree today; nothing prevents future drift.
- `unitParser.ts` has **no conversion factors for SQM/SQYD** (area units) despite recognizing/normalizing them — any quantity comparison needing an area conversion silently falls to "needs review" with no explanation surfaced to the auditor.
- Excel/date parsing fragility (§I‑#9/#10) is a data-integrity risk at the point of entry, before any calculation runs.
- The snapshot's complete absence of downstream data (§C) means **none of the calculation engines above have been validated against a real, full audit** — every formula-correctness finding in this report is a static-analysis result, not an observed-in-production result.

## L. Security & Privacy Risks

- **RBAC non-enforcement is the headline security finding.** `convex/lib/rbac.ts`'s `requireEditor`/`requireReviewer`/`requireAdmin`/`requireAuditAccess`/`canUserPerform` are imported **only by `convex/users.ts`** (for `updateRole`), verified by grep across the entire `convex/` tree. Every other mutation file uses one of three different ad hoc auth patterns instead: (a) `requireUser` (from `users.ts`, itself a thin re-export of `rbac.ts`'s `getCurrentUserOrThrow` — authentication only, no role check) — used by `dutyAssessment.ts`, `excessDetection.ts`, `findings.ts`, `matching.ts`, `entitlements.ts`, `imports.ts`, `bondRegister.ts`, `bondRegistrar.ts`, `dutyRateRegistry.ts`, `schedule3b.ts`, `schedule4.ts`, `vaCalculator.ts`, `notes.ts`, `companies.ts`, `documents.ts`, `audits.ts`; (b) a **locally copy-pasted `requireAuth`** function, independently redefined in `docRequests.ts`, `checklist.ts`, and `udUp.ts` (three copies of the same ~5-line function); (c) **nothing**, in `schedules.ts`'s `updateRow`/`clearSchedule`/`deleteRow` (§I‑#1). Net effect: the documented "16 actions × 4 roles" matrix restricts almost nothing at the server. A "viewer" account, or in the `schedules.ts` case an anonymous client, can perform actions the UI hides but the backend does not gate.
- **No audit-lock enforcement** in any calculation engine (§I‑#7) — a "locked" audit is not actually immutable.
- **Privacy guard (`applyPrivacyGuard`) is real but inconsistent between the two agents**: the Audit Agent masks `be`/`b/e`/`im-4`/`im4` patterns and 9–12 digit IDs, applied to the *user's message* before it reaches the model (chat.ts:524-528); Free Chat masks the same ID pattern but not `im-4`/`im4`, and applies the two replacements in the opposite order (freeChat/chat.ts:186-190). Low practical severity (order rarely changes the outcome) but confirms the two implementations were hand-copied rather than shared.
- **Client-side "RBAC mirror" is not actually a mirror.** `src/hooks/use-permissions.ts` has no logic of its own — it's a query wrapper around `users.ts:getMyPermissions`. The real duplication is server-side: `getMyPermissions` (users.ts:90-121) hand-maintains its own inline role matrix, separate from `rbac.ts`'s (dead) `canUserPerform` matrix. They agree today; nothing keeps them in sync if either changes.
- **Auth secrets**: no secret values are present in the reviewed package (only key *names*, e.g. `HERCULES_API_KEY`), consistent with the docs' claim — no leaked-credential finding.

## M. Performance & Token-Cost Problems

- **~35,000+ input tokens of system-message content on every single AI call**, from both agents, regardless of question complexity or audit type (§D). This repeats on every iteration of the Audit Agent's up-to-5-iteration tool loop.
- **No retrieval/RAG** — the entire SRO 212 + SRO 213 + 7-module master knowledge base (129,499 characters) is sent whole every time; a Non‑RMG audit pays for RMG-specific content and vice versa.
- **Tool result truncation without signaling**: `get_open_findings` caps at 100, `get_non_entitled_imports` at 50, `get_schedule_data` at 100, `get_import_details` at 50, `get_unmatched_items` at 30 — confirmed exactly as coded. For any audit whose real record count exceeds these, the agent reasons over a silently incomplete picture with no "this is truncated" signal passed to the model.
- **Service worker precaches only `offline.html` + 4 icons** (§I‑#8 context) — no app-shell JS/CSS bundle is precached, and navigation requests are network-only with no cache fallback, so even a page the user already visited is unavailable offline; only the static placeholder ever appears.
- **Frontend test coverage is 0%** across ~34,000 lines (`vitest.config.ts` is correctly configured with `passWithNoTests: true`, which means this has been silently "passing" in CI the entire time rather than failing loudly). Backend: 3 of 42 non-generated Convex files have a test (~7%).

## N. Duplicate / Conflicting Logic (summary — details are in §I/§J/§K/§L)

| Logic | Copies | Currently agree? |
|---|---|---|
| Duty cascade (CD/RD/SD/VAT/AT/AIT) | 4 (`dutyAssessment.ts`, `dutyRateRegistry.ts`, agent tool, `audit-procedures.ts`) | Yes |
| Closing stock aggregation | 2 (`closingStock.ts`, `reports.ts`) | Yes (sort order only differs) |
| VA% formula | 3 (`vaCalculator.ts`, `schedule3b.ts`, orphaned `assessment-formulas.ts`/T‑06) | **No** — two different denominators |
| VA% aggregate statistic | 2 (`vaCalculator.getSummary` unweighted mean, `word-report-builder.ts` value-weighted) | **No** — structurally guaranteed to differ |
| Excess-detection algorithm | 2 (`excessDetection.ts` live; orphaned `test-t04.ts`) | **No** — different entitlement base and valuation method, but the second copy is currently unreachable |
| "Is user logged in" helper | 3 names, 4+ definitions (`rbac.ts:getCurrentUserOrThrow`, `users.ts:requireUser` wrapper, `requireAuth` copy-pasted in 3 files) | Functionally yes, but pure duplication |
| Client RBAC "mirror" vs. server matrix | 2 (`users.ts:getMyPermissions` inline matrix, `rbac.ts:canUserPerform`, the latter dead) | Yes today |

---

## O. Existing Code That Should NOT Be Rewritten

- **The duty cascade** (`dutyAssessment.ts`, `dutyRateRegistry.ts`) — correct, consistent across all 4 copies, matches the documented NBR formula. Consolidate the copies later; don't rewrite the formula.
- **Bond register reconciliation** (`bondRegister.ts`) and its 0.5%/2% thresholds — verified exactly as coded and legally grounded.
- **Schedule‑4 wastage variance math** (`schedule4.ts`) — verified exactly as coded, including the `variance > 0.001` excess threshold.
- **The 5-level matcher** (`convex/lib/matcher.ts`) — thresholds (70%/45%) and tier order verified correct; the synonym dictionary is a reasonable, working design even if it will always need extension.
- **`calculate_duty` as an AI tool pattern** — forcing the model through a deterministic function instead of letting it do arithmetic is exactly the right shape and should be the template extended to other calculations, not replaced.
- **The Word report's `PARA_NUM` cross-reference system** — a genuinely good design (body sections and review/opinion sections cite each other by paragraph number) and confirmed working as intended.
- **The orphaned audit-engine's actual test logic** (T‑01 through T‑13) — where it doesn't conflict with the live engines (§N), the implementations read as careful, evidence-aware code (e.g., T‑07's three-way LC triangulation correctly requires ≥2 of 3 sources before drawing a conclusion, and skips cleanly with a stated reason otherwise). This is worth *reconnecting and reconciling*, not discarding — see §R.
- **The BondAudit‑FastAPI system's evidence-model discipline** (§B) — "never invent a conversion factor, flag `REVIEW_REQUIRED` instead," "AI can reach SUGGESTED, never APPROVED," services that never import the web framework — is a genuinely good architectural pattern worth importing conceptually into BondAudit‑Convex, even though the two codebases shouldn't be merged.

---

## P. Recommended Architecture (direction, not a rewrite plan)

1. **Pick one system as canonical.** BondAudit‑Convex has the feature breadth and the only real pilot data; BondAudit‑FastAPI has the evidence-first discipline and a self-hosted stack with no vendor dependency on Convex/Hercules. If the organization's target is the full lifecycle described in the brief (OCR→…→Word/Excel report), BondAudit‑Convex is closer to done and should be the base — but its RBAC/lock/duplicate-calc gaps (§L, §N) need closing before it can be trusted as authoritative, and BondAudit‑FastAPI's "never persist a number without evidence, AI suggests-only" discipline should be retrofitted onto it rather than re-derived from scratch.
2. **Draw a hard line between deterministic engines and the AI layer**, and make it structural, not just conventional: every write path that currently accepts a number from the model (`fill_schedule`, `fill_schedule4`) should either (a) require the corresponding `validate_schedule`-equivalent check to run synchronously in the same mutation, not as a separate optional tool call, or (b) have its numeric fields server-computed from linked source rows rather than accepted verbatim from the model's tool-call arguments.
3. **Consolidate the 4 auth-helper implementations into one**, imported everywhere, with `requireEditor`/`requireReviewer`/`requireAdmin`/`requireAuditAccess` actually wired into every mutation, and an `ensure_audit_not_locked`-equivalent check added at the top of every engine mutation — this single change would close §I‑#1, #6, #7 simultaneously.
4. **One VA% formula, one closing-stock function, one duty-cascade function** — each currently duplicated 2-4 ways; pick the correct version (VA% needs a legal decision first — FOB or input denominator — flagged **VERIFY REQUIRED**), delete the others, have every consumer call the single source.
5. **Reconnect or formally retire the orphaned audit-engine** — as-is it's neither used nor deletable-without-loss (T‑07's triangulation logic doesn't exist anywhere else). Reconcile its excess/VA formulas with the live engines' before wiring it up, or the moment it's connected it introduces the very inconsistencies in §I‑#4/#N live.

## Q. Required Database Changes

- Rename or clearly namespace `audits.scheduleType` vs. `schedule_records.scheduleType` (§C) — same field name, two unrelated enums.
- Decide and enforce a single source of truth between `potentialDutyDemand` and `dutyDemand`, or merge them into one field with a `source` tag (`"assessment"` vs `"registry"`) so a report can show *which* number it's displaying and why.
- Add a `lockedFields`/mutation-guard convention at the schema or middleware layer so "an audit is locked" is enforced once, not per-engine.
- No urgent schema *shape* changes are needed for Schedule‑4's typed-table vs. other-schedules'-JSON-blob split (§C) — it's a legitimate, if inconsistent, design; only worth revisiting if query-by-column becomes a real need for the other schedules.

## R. Required Audit Engine Improvements

- Fix the VA% three-way disagreement (§I‑#2/#4) — this is the single highest-value correctness fix in the codebase.
- Resolve `potentialDutyDemand`/`dutyDemand` (§I‑#3).
- Add `SQM`/`SQYD` conversion factors to `unitParser.ts`, or explicitly document why area units can't convert.
- Reconcile the orphaned `test-t04.ts`'s excess-detection method (flat total, average unit price, three-field entitlement base) against the live `excessDetection.ts` (chronological, per-B/E actual value, single-field entitlement base) before any reconnection.
- Fix the Excel/date parsing fragility (§I‑#9/#10) — unify the two header-scan limits, add real merged-cell handling or explicitly document its absence, and add date-format validation/auto-detection.

## S. Required AI/RAG Improvements

- Replace the "send the entire knowledge base every time" pattern with retrieval scoped to the audit's actual `institutionType`/`scheduleType` (SRO 212 vs. 213 content alone would likely cut the base knowledge payload substantially) and, longer-term, semantic retrieval over the legal text rather than string constants.
- Signal truncation explicitly in tool results (`get_open_findings`, etc.) so the model knows when it's reasoning over a partial dataset rather than silently treating 100 items as "all of them."
- Fix the T‑09 AT-formula prompt self-contradiction (§D) — a one-line prompt edit.
- Unify the two `applyPrivacyGuard` implementations into one shared function.
- Require `validate_schedule` (or equivalent) to run automatically after `fill_schedule`/`fill_schedule4`, and log every AI-driven write to `audit_trail` (§D) so AI decisions are as traceable as human ones.

## T. Required Self-Learning Improvements

The pipeline (`training_examples` capture, 15-day cron reports) is real infrastructure with no consumer — `exportAll` produces JSONL that nothing reads. Before investing further: (1) decide whether fine-tuning is actually the goal, since the current `temperature: 0.1` + tool-forced-calculation architecture may get more value from better prompts/retrieval than from fine-tuning; (2) if fine-tuning is the goal, build the missing review/approval UI for collected examples — right now the model self-scores its own training examples (§D, `save_training_example`) with no human-in-the-loop check, which risks reinforcing whatever the model already tends to do, including any of the inconsistencies flagged in §D/§I.

## U. Production Readiness Assessment

**Not production-ready**, for reasons independent of feature completeness:

- No real audit has ever been carried through the full pipeline in the observed data (§C) — every calculation-correctness finding above is unvalidated against real end-to-end use.
- RBAC and audit-lock are not enforced (§L) — this alone should block any multi-user or externally-facing deployment.
- 0% frontend test coverage and ~7% backend coverage, with `passWithNoTests: true` silently masking the frontend gap in CI (§M).
- A live, structural numeric disagreement exists between two screens an auditor would reasonably compare side-by-side (VA%, §I‑#2) and a real silent-zero risk in the legal report deliverable (§I‑#3) — these are the kind of defects that damage trust in a customs-audit tool specifically, where a wrong number in a filed report has legal consequences.
- The PWA offline story is effectively cosmetic (§I‑#8, §M) — fine for a nice-to-have, not something to represent as "works offline."

What *is* production-grade: the core deterministic calculation code itself (duty cascade, bond register, schedule‑4, matcher), the schema design, and the AI agents' guardrails around hallucination and privacy masking (imperfect in detail, sound in intent).

## V. Prioritized Roadmap

**P0 — must fix before any real multi-user or filed-report use:**
1. Add auth to `schedules.ts`'s `updateRow`/`clearSchedule`/`deleteRow` (§I‑#1).
2. Wire `rbac.ts`'s role checks and an audit-lock check into every mutating engine (§L, §I‑#6/#7).
3. Resolve the VA% three-formula conflict and pick one canonical implementation (§I‑#2/#4, §J).
4. Resolve `potentialDutyDemand` vs `dutyDemand` so the report can never silently show ৳0 (§I‑#3).

**P1 — important, plan for the next development cycle:**
5. Consolidate the duplicated duty-cascade, closing-stock, and auth-helper implementations (§N).
6. Fix Excel/date parsing fragility; unify header-scan limits (§I‑#9/#10).
7. Fix the T‑09 AT-formula prompt contradiction (§D).
8. Replace the hardcoded ৳110 exchange rate with a real, sourced lookup (§I‑#5).
9. Bring backend test coverage up on the untested core engines, starting with a test that actually varies `atRate` (§I‑#11, §M).
10. Add AI-write logging to `audit_trail` (§D, §S).

**P2 — enhancement:**
11. Reconnect or formally retire the orphaned audit-engine, after reconciling its formulas (§H, §R).
12. Fix the duplicated service-worker event listeners (§I‑#8).
13. Add RAG/scoped retrieval to cut AI token cost (§M, §S).
14. Bring frontend test coverage above 0% (§M).

**P3 — future:**
15. Decide the long-term relationship between BondAudit‑Convex and BondAudit‑FastAPI (§B, §P).
16. Build the missing bulk-edit/bulk-confirm UI (§G).
17. Build a real fine-tuning consumer for the training-example pipeline, with human review added first (§T).
18. Complete the partial তফসিল‑৩(ক)/৫/RMG schedule UIs (§G).

---

**SYSTEM AUDIT COMPLETE — READY FOR PHASE-2**

No code, schema, or data was modified to produce this report. Phase‑2 implementation work should begin only on your explicit go-ahead, and — per your own instructions — should start with the P0 items in §V, in the order listed, since each is independently a data-integrity or security issue rather than a cosmetic one.
