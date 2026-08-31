"use client";

import { ChangeEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { AuditNav } from "@/components/features/audit-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { api, ApiError } from "@/lib/api";
import type { ColumnMappingSuggestions, DocumentType, SourceDocument } from "@/lib/types";

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: "entitlement_sheet", label: "Entitlement Sheet" },
  { value: "enhanced_entitlement", label: "Enhanced Entitlement" },
  { value: "import_mis", label: "Import MIS" },
  { value: "bill_of_entry", label: "Bill of Entry" },
  { value: "other", label: "Other" },
];

export default function DocumentsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState<DocumentType>("entitlement_sheet");
  const [uploading, setUploading] = useState(false);

  const [selectedDocument, setSelectedDocument] = useState<SourceDocument | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [suggestions, setSuggestions] = useState<ColumnMappingSuggestions | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  function reload() {
    api.documents
      .list(auditId)
      .then(setDocuments)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load documents"));
  }

  useEffect(reload, [auditId]);

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await api.documents.upload(auditId, file, documentType);
      setMessage(`Uploaded ${file.name}`);
      setFile(null);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function loadSuggestions(doc: SourceDocument, sheet: string) {
    setSelectedDocument(doc);
    setSelectedSheet(sheet);
    setSuggestions(null);
    setError(null);
    try {
      const result = await api.documents.mappingSuggestions(auditId, doc.id, sheet);
      setSuggestions(result);
      const initialMapping: Record<string, string> = {};
      for (const s of result.suggestions) {
        if (s.suggested_target_field) initialMapping[s.source_header] = s.suggested_target_field;
      }
      setMapping(initialMapping);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load mapping suggestions");
    }
  }

  async function confirmMapping() {
    if (!selectedDocument) return;
    const mappings = Object.entries(mapping)
      .filter(([, target]) => target)
      .map(([source_header, target_field]) => ({ source_header, target_field }));
    if (mappings.length === 0) {
      setError("Map at least one column before confirming.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.documents.confirmMapping(auditId, selectedDocument.id, selectedSheet, mappings);
      setMessage("Mapping confirmed.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to confirm mapping");
    } finally {
      setBusy(false);
    }
  }

  async function runParse() {
    if (!selectedDocument) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      if (selectedDocument.document_type === "entitlement_sheet") {
        const result = await api.entitlement.parse(auditId, selectedDocument.id, selectedSheet);
        setMessage(`Entitlement master built: ${JSON.stringify(result)}`);
      } else if (selectedDocument.document_type === "import_mis") {
        const result = await api.imports.parse(auditId, selectedDocument.id, selectedSheet);
        setMessage(`Import transactions parsed: ${JSON.stringify(result)}`);
      } else {
        setMessage("This document type doesn't have an automatic parse step yet — use it as evidence on the relevant pages.");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Parse failed — confirm the column mapping first.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <AuditNav auditId={auditId} />
      {error && <Alert className="mb-4">{error}</Alert>}
      {message && <p className="mb-4 rounded-md bg-muted p-3 text-sm">{message}</p>}

      <Card>
        <CardHeader>
          <CardTitle>Upload document</CardTitle>
          <CardDescription>Entitlement sheet, Import MIS, or other bond audit evidence.</CardDescription>
        </CardHeader>
        <CardContent className="flex items-end gap-4">
          <div>
            <Label htmlFor="doc_type">Document type</Label>
            <Select id="doc_type" value={documentType} onChange={(e) => setDocumentType(e.target.value as DocumentType)}>
              {DOCUMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="file">File</Label>
            <Input
              id="file"
              type="file"
              accept=".xlsx,.xls"
              onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <Button onClick={handleUpload} disabled={!file || uploading}>
            {uploading ? "Uploading…" : "Upload"}
          </Button>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Uploaded documents</CardTitle>
        </CardHeader>
        <CardContent>
          {documents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No documents uploaded yet.</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>File</Th>
                  <Th>Type</Th>
                  <Th>Sheets</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {documents.map((doc) => (
                  <Tr key={doc.id}>
                    <Td>{doc.original_filename}</Td>
                    <Td>
                      <Badge tone="muted">{doc.document_type}</Badge>
                    </Td>
                    <Td className="space-x-2">
                      {(doc.sheet_names ?? []).map((sheet) => (
                        <button
                          key={sheet}
                          className="text-sm underline"
                          onClick={() => loadSuggestions(doc, sheet)}
                        >
                          {sheet}
                        </button>
                      ))}
                    </Td>
                    <Td />
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardContent>
      </Card>

      {suggestions && selectedDocument && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle>
              Column mapping — {selectedDocument.original_filename} / {selectedSheet}
            </CardTitle>
            <CardDescription>Confirm or correct the suggested mapping before parsing (spec section 10: never auto-approve).</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <Thead>
                <Tr>
                  <Th>Source column</Th>
                  <Th>Suggested field</Th>
                  <Th>Confidence</Th>
                  <Th>Confirmed target field</Th>
                </Tr>
              </Thead>
              <Tbody>
                {suggestions.suggestions.map((s) => (
                  <Tr key={s.source_header}>
                    <Td>{s.source_header}</Td>
                    <Td className="text-muted-foreground">{s.suggested_target_field ?? "—"}</Td>
                    <Td>{(s.confidence * 100).toFixed(0)}%</Td>
                    <Td>
                      <Select
                        value={mapping[s.source_header] ?? ""}
                        onChange={(e) => setMapping((m) => ({ ...m, [s.source_header]: e.target.value }))}
                      >
                        <option value="">— skip —</option>
                        {suggestions.available_target_fields.map((f) => (
                          <option key={f} value={f}>
                            {f}
                          </option>
                        ))}
                      </Select>
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
            <div className="mt-4 flex gap-3">
              <Button onClick={confirmMapping} disabled={busy}>
                Confirm mapping
              </Button>
              <Button variant="outline" onClick={runParse} disabled={busy}>
                {busy ? "Working…" : "Parse with confirmed mapping"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </AppShell>
  );
}
