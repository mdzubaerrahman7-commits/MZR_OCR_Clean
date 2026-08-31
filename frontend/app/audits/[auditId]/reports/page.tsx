"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { AuditNav } from "@/components/features/audit-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { api, ApiError, downloadBlob } from "@/lib/api";
import type { ReportHistoryEntry } from "@/lib/types";

const OUTPUTS: { code: string; label: string }[] = [
  { code: "output-01", label: "Output 01 — Raw Material Detailed Import Statement" },
  { code: "output-02", label: "Output 02 — Imported Raw Material Summary" },
  { code: "output-03", label: "Output 03 — Machinery & Sample Import Statement" },
  { code: "output-04", label: "Output 04 — Reconciliation & Exception Dashboard" },
  { code: "output-05", label: "Output 05 — Non-Entitled Import B/E-wise Duty Assessment" },
  { code: "output-06", label: "Output 06 — Excess Import B/E-wise Duty Assessment" },
  { code: "output-07", label: "Output 07 — Import Audit Findings Register" },
];

export default function ReportsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [history, setHistory] = useState<ReportHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);

  function reload() {
    api.reports
      .history(auditId)
      .then(setHistory)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load report history"));
  }

  useEffect(reload, [auditId]);

  async function generate(code: string) {
    setGenerating(code);
    setError(null);
    try {
      const blob = await api.reports.generate(auditId, code);
      downloadBlob(blob, `${code.toUpperCase().replace("-", "_")}.xlsx`);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate report");
    } finally {
      setGenerating(null);
    }
  }

  return (
    <AppShell>
      <AuditNav auditId={auditId} />
      {error && <Alert className="mb-4">{error}</Alert>}

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Excel outputs</CardTitle>
          <CardDescription>Each generation is recorded with the source audit ID and timestamp (spec section 19).</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {OUTPUTS.map((o) => (
            <Button key={o.code} variant="outline" disabled={generating === o.code} onClick={() => generate(o.code)}>
              {generating === o.code ? "Generating…" : o.label}
            </Button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Generation history</CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">No reports generated yet.</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>Output</Th>
                  <Th>Generated at</Th>
                </Tr>
              </Thead>
              <Tbody>
                {history.map((h) => (
                  <Tr key={h.id}>
                    <Td>{h.output_code}</Td>
                    <Td>{new Date(h.generated_at).toLocaleString()}</Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
