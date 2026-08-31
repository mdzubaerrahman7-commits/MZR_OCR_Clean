// Thin typed fetch wrapper over the FastAPI backend. Every audit-scoped call takes
// auditId explicitly rather than baking a "current audit" into this module, so pages
// stay simple server/client components without a hidden global.

import type {
  Audit,
  BillOfEntry,
  ColumnMappingSuggestions,
  Company,
  EntitlementGroup,
  EntitlementItem,
  ExceptionDashboard,
  Finding,
  ImportTransaction,
  ReportHistoryEntry,
  SourceDocument,
  User,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "bondaudit_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  else window.localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function requestBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) throw new ApiError(response.status, response.statusText);
  return response.blob();
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return "?" + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      request<{ access_token: string; user: User }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      }),
    bootstrapAdmin: (email: string, password: string, full_name: string) =>
      request<User>("/api/auth/bootstrap-admin", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),
    me: () => request<User>("/api/auth/me"),
  },

  companies: {
    list: () => request<Company[]>("/api/companies"),
    create: (payload: { name: string; bin_number: string; bond_license_number: string; facility_type?: string; address?: string }) =>
      request<Company>("/api/companies", { method: "POST", body: JSON.stringify(payload) }),
    get: (id: string) => request<Company>(`/api/companies/${id}`),
  },

  audits: {
    list: (companyId?: string) => request<Audit[]>(`/api/audits${qs({ company_id: companyId })}`),
    get: (id: string) => request<Audit>(`/api/audits/${id}`),
    create: (payload: {
      company_id: string;
      audit_code: string;
      title: string;
      audit_period_start: string;
      audit_period_end: string;
      entitlement_period_start: string;
      entitlement_period_end: string;
    }) => request<Audit>("/api/audits", { method: "POST", body: JSON.stringify(payload) }),
    lock: (id: string, reason?: string) => request<Audit>(`/api/audits/${id}/lock`, { method: "POST", body: JSON.stringify({ reason }) }),
  },

  documents: {
    list: (auditId: string) => request<SourceDocument[]>(`/api/audits/${auditId}/documents`),
    upload: (auditId: string, file: File, documentType: string) => {
      const form = new FormData();
      form.append("file", file);
      form.append("document_type", documentType);
      return request<SourceDocument>(`/api/audits/${auditId}/documents`, { method: "POST", body: form });
    },
    mappingSuggestions: (auditId: string, documentId: string, sheetName: string) =>
      request<ColumnMappingSuggestions>(
        `/api/audits/${auditId}/documents/${documentId}/mapping-suggestions${qs({ sheet_name: sheetName })}`
      ),
    confirmMapping: (
      auditId: string,
      documentId: string,
      sheetName: string,
      mappings: { source_header: string; target_field: string }[],
      saveAsTemplateName?: string
    ) =>
      request(`/api/audits/${auditId}/documents/${documentId}/confirm-mapping`, {
        method: "POST",
        body: JSON.stringify({ sheet_name: sheetName, mappings, save_as_template_name: saveAsTemplateName }),
      }),
  },

  entitlement: {
    list: (auditId: string) => request<EntitlementGroup[]>(`/api/audits/${auditId}/entitlement`),
    parse: (auditId: string, sourceDocumentId: string, sheetName: string) =>
      request(`/api/audits/${auditId}/entitlement/parse`, {
        method: "POST",
        body: JSON.stringify({ source_document_id: sourceDocumentId, sheet_name: sheetName }),
      }),
  },

  imports: {
    parse: (auditId: string, sourceDocumentId: string, sheetName: string) =>
      request(`/api/audits/${auditId}/imports/parse`, {
        method: "POST",
        body: JSON.stringify({ source_document_id: sourceDocumentId, sheet_name: sheetName }),
      }),
    list: (auditId: string, params: { classification?: string; review_required?: boolean } = {}) =>
      request<ImportTransaction[]>(`/api/audits/${auditId}/imports${qs(params)}`),
    overrideClassification: (auditId: string, transactionId: string, classification: string, reason: string) =>
      request<ImportTransaction>(`/api/audits/${auditId}/imports/${transactionId}/classification`, {
        method: "PATCH",
        body: JSON.stringify({ classification, reason }),
      }),
    matchCandidates: (auditId: string, transactionId: string) =>
      request<EntitlementItem[]>(`/api/audits/${auditId}/imports/${transactionId}/match-candidates`),
    confirmMatch: (auditId: string, transactionId: string, decision: string, entitlementItemId?: string, reason?: string) =>
      request<ImportTransaction>(`/api/audits/${auditId}/imports/${transactionId}/match/confirm`, {
        method: "POST",
        body: JSON.stringify({ decision, entitlement_item_id: entitlementItemId, reason }),
      }),
  },

  billOfEntries: {
    list: (auditId: string) => request<BillOfEntry[]>(`/api/audits/${auditId}/bill-of-entries`),
    upsert: (auditId: string, payload: Record<string, unknown>) =>
      request<BillOfEntry>(`/api/audits/${auditId}/bill-of-entries`, { method: "POST", body: JSON.stringify(payload) }),
  },

  rules: {
    matchEntitlements: (auditId: string) => request(`/api/audits/${auditId}/match-entitlements`, { method: "POST" }),
    calculateConversions: (auditId: string) => request(`/api/audits/${auditId}/calculate-conversions`, { method: "POST" }),
    classify: (auditId: string) => request(`/api/audits/${auditId}/classify`, { method: "POST" }),
    detectExcess: (auditId: string) => request(`/api/audits/${auditId}/detect-excess`, { method: "POST" }),
    exceptions: (auditId: string) => request<ExceptionDashboard>(`/api/audits/${auditId}/exceptions`),
  },

  findings: {
    generate: (auditId: string) => request(`/api/audits/${auditId}/generate-findings`, { method: "POST" }),
    list: (auditId: string, params: { issue_type?: string; review_status?: string } = {}) =>
      request<Finding[]>(`/api/audits/${auditId}/findings${qs(params)}`),
    review: (auditId: string, findingId: string, decision: string, reason?: string) =>
      request<Finding>(`/api/audits/${auditId}/findings/${findingId}/review`, {
        method: "PATCH",
        body: JSON.stringify({ decision, reason }),
      }),
  },

  reports: {
    generate: (auditId: string, outputCode: string) => requestBlob(`/api/audits/${auditId}/reports/${outputCode}`, { method: "POST" }),
    history: (auditId: string) => request<ReportHistoryEntry[]>(`/api/audits/${auditId}/reports/history`),
  },
};

export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
