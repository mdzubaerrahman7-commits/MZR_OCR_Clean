// Mirrors backend/app/schemas/*.py. Kept hand-in-sync deliberately (no codegen step
// in this environment) — when a backend schema changes, update the matching type here.

export type Role = "administrator" | "auditor" | "reviewer" | "viewer";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: string;
  name: string;
  bin_number: string;
  bond_license_number: string;
  facility_type: string;
  address: string | null;
  created_at: string;
  updated_at: string;
}

export type AuditStatus = "draft" | "in_progress" | "locked";

export interface Audit {
  id: string;
  company_id: string;
  audit_code: string;
  title: string;
  audit_period_start: string;
  audit_period_end: string;
  entitlement_period_start: string;
  entitlement_period_end: string;
  status: AuditStatus;
  created_by: string;
  locked_at: string | null;
  locked_by: string | null;
  created_at: string;
  updated_at: string;
}

export type DocumentType = "import_mis" | "entitlement_sheet" | "enhanced_entitlement" | "bill_of_entry" | "other";

export interface SourceDocument {
  id: string;
  audit_id: string;
  document_type: DocumentType;
  original_filename: string;
  checksum_sha256: string;
  content_type: string | null;
  sheet_names: string[] | null;
  uploaded_by: string;
  uploaded_at: string;
  supersedes_id: string | null;
}

export interface MappingSuggestion {
  source_header: string;
  suggested_target_field: string | null;
  confidence: number;
}

export interface ColumnMappingSuggestions {
  sheet_name: string;
  header_row_index: number;
  available_target_fields: string[];
  suggestions: MappingSuggestion[];
  preview_rows: Record<string, unknown>[];
}

export interface EntitlementItem {
  id: string;
  group_id: string;
  sequence_no: number;
  material_name: string;
  hs_code: string;
  entitlement_unit: string;
  annual_entitlement_qty: string;
  enhanced_entitlement_qty: string;
  total_entitlement_qty: string;
  active: boolean;
  source_row_number: number | null;
  created_at: string;
  updated_at: string;
}

export interface EntitlementGroup {
  id: string;
  audit_id: string;
  sequence_no: number;
  group_name: string;
  group_code: string | null;
  notes: string | null;
  items: EntitlementItem[];
  created_at: string;
  updated_at: string;
}

export type Classification = "raw_material" | "machinery" | "sample" | "spare_consumable" | "unknown";
export type MatchStatus = "unmatched" | "suggested" | "approved" | "rejected" | "review_required";
export type ExcessStatus = "not_applicable" | "within_entitlement" | "partial_excess" | "full_excess";

export interface ImportTransaction {
  id: string;
  audit_id: string;
  source_document_id: string;
  source_row_number: number;
  be_number: string;
  be_date: string;
  import_date: string | null;
  lc_number: string | null;
  invoice_number: string | null;
  item_description: string;
  hs_code: string;
  declared_quantity: string;
  declared_unit: string;
  entitlement_item_id: string | null;
  match_status: MatchStatus;
  match_confidence: string | null;
  match_evidence: string | null;
  entitlement_quantity: string | null;
  entitlement_unit: string | null;
  kg_quantity: string | null;
  original_currency: string | null;
  original_currency_value: string | null;
  usd_value: string | null;
  assessable_value: string | null;
  conversion_evidence: string | null;
  classification: Classification;
  classification_confidence: string;
  non_entitled: boolean;
  excess_status: ExcessStatus;
  excess_quantity: string | null;
  allowed_quantity: string | null;
  cumulative_quantity_after: string | null;
  review_status: string;
  created_at: string;
  updated_at: string;
}

export interface ExceptionDashboard {
  non_entitled_count: number;
  review_required_match_count: number;
  unknown_classification_count: number;
  partial_excess_count: number;
  full_excess_count: number;
  conversion_incomplete_count: number;
  non_entitled_transactions: ImportTransaction[];
  review_required_transactions: ImportTransaction[];
  excess_transactions: ImportTransaction[];
  conversion_incomplete_transactions: ImportTransaction[];
}

export interface Finding {
  id: string;
  audit_id: string;
  finding_code: string;
  issue_type: string;
  evidence: string;
  bill_of_entry_id: string | null;
  import_transaction_id: string | null;
  entitlement_item_id: string | null;
  material_name: string | null;
  quantity: string | null;
  unit: string | null;
  value: string | null;
  demand_amount: string | null;
  review_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BillOfEntry {
  id: string;
  audit_id: string;
  be_number: string;
  be_date: string;
  conversion_evidence: string | null;
  exchange_rate: string | null;
  exchange_rate_evidence: string | null;
  kg_conversion_factor: string | null;
  kg_conversion_evidence: string | null;
  entitlement_conversion_factor: string | null;
  entitlement_conversion_evidence: string | null;
  assessable_value: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportHistoryEntry {
  id: string;
  output_code: string;
  generated_by: string;
  generated_at: string;
}
