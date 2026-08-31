# Data Model — Import Audit Module 01

Source of truth: `backend/app/models/*.py` (SQLAlchemy). This is a narrative index,
not a duplicate schema — see the model files for exact column types/nullability, and
`backend/alembic/versions/0001_initial.py` for the migration (generated from the
models themselves, not hand-typed, so it can't drift from them).

## Identity & access

- **users** — email, hashed_password, full_name, `role` (administrator / auditor /
  reviewer / viewer, spec section 20), is_active.
- **companies** — name, BIN, bond license number, facility_type, address.
- **audits** — belongs to a company; audit_period_start/end, entitlement_period_start/end,
  status (draft / in_progress / locked), created_by, locked_at/locked_by. Locking is
  one-way (`audits.lock` endpoint) — every mutating engine checks `ensure_audit_not_locked`
  first.
- **audit_log_entries** — the audit trail (spec section 19): entity_type/entity_id,
  action, old_value/new_value (JSON), user_id, reason. Append-only; written by
  `services/audit_trail.record()` from every router that changes state.

## Layer A — raw evidence

- **source_documents** — one row per uploaded file: storage_key (content-addressed),
  checksum_sha256, sheet_names, uploaded_by/at, `supersedes_id` (a re-upload never
  overwrites — it points at the version it replaces).
- **column_mapping_templates** / **column_mapping_template_fields** — reusable, named
  header→field mappings (M03).
- **document_column_mappings** — the mapping an auditor actually confirmed for one
  document+sheet; this is what `entitlement/parse` and `imports/parse` read.

## Master data

- **entitlement_groups** — audit_id, sequence_no (authoritative order — never re-sorted),
  group_name/code, source_document_id.
- **entitlement_items** — group_id, sequence_no, material_name, hs_code (string, to
  preserve leading zeros), entitlement_unit, annual/enhanced/total_entitlement_qty
  (Numeric/Decimal), source_document_id + source_row_number (evidence pointer back to
  the raw sheet).

## Layer B/C — normalized transactions and derived results

- **import_transactions** — one row per in-audit-period B/E line. Raw fields
  (be_number, be_date, hs_code, declared_quantity/unit, ...) plus every engine's
  working output on the same row: `classification`/`classification_confidence` (M05),
  `entitlement_item_id`/`match_status`/`match_confidence`/`match_evidence` (M06),
  `entitlement_quantity`/`kg_quantity`/`usd_value`/`conversion_evidence` (M07,
  null until evidence exists — never guessed), `non_entitled`/`excess_status`/
  `allowed_quantity`/`excess_quantity`/`cumulative_quantity_after` (M08). `raw_payload`
  (JSON) keeps the original spreadsheet row for evidence.
- **bill_of_entries** — audit_id + be_number (unique together), the conversion/exchange
  evidence M07 requires (`exchange_rate`, `kg_conversion_factor`,
  `entitlement_conversion_factor`, each with a paired `*_evidence` text field), and
  `assessable_value`.
- **duty_components** — belongs to a bill_of_entry: component_code (CD/RD/SD/VAT/AIT/AT/...),
  rate, base_amount, calculated_amount, source_evidence.
- **findings** — the findings register (OUTPUT 07): finding_code, issue_type
  (non_entitled / excess_partial / excess_full / classification_review / ...),
  evidence, links back to bill_of_entry/import_transaction/entitlement_item,
  quantity/unit/value/demand_amount, review_status/reviewed_by/reviewed_at.
- **generated_reports** — output_code, storage_key, generated_by/at (spec section 19:
  every generated report records its source audit ID and generation time).

## Why UUID-as-`String(36)` primary keys

Every table uses a `String(36)` UUID primary key (`db/base.py::UUIDPrimaryKeyMixin`)
rather than the PostgreSQL-only `UUID` column type, so the exact same models run
against SQLite (fast, dependency-free unit tests) and PostgreSQL (every real
deployment) without a dialect branch.
