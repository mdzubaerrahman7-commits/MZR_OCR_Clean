"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { AuditNav } from "@/components/features/audit-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { hasPermissionHint, useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { Finding } from "@/lib/types";

const REVIEW_TONE: Record<string, "muted" | "warning" | "success" | "danger"> = {
  open: "warning",
  under_review: "muted",
  approved: "success",
  rejected: "danger",
};

export default function FindingsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const { user } = useAuth();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  function reload() {
    api.findings
      .list(auditId)
      .then(setFindings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load findings"));
  }

  useEffect(reload, [auditId]);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const result = await api.findings.generate(auditId);
      setMessage(`Findings regenerated: ${JSON.stringify(result)}`);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate findings");
    } finally {
      setGenerating(false);
    }
  }

  async function review(findingId: string, decision: "approved" | "rejected") {
    setBusyId(findingId);
    setError(null);
    try {
      await api.findings.review(auditId, findingId, decision);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record review decision");
    } finally {
      setBusyId(null);
    }
  }

  const canReview = hasPermissionHint(user?.role, ["administrator", "reviewer"]);

  return (
    <AppShell>
      <AuditNav auditId={auditId} />
      {error && <Alert className="mb-4">{error}</Alert>}
      {message && <p className="mb-4 rounded-md bg-muted p-3 text-sm">{message}</p>}

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Findings Register</CardTitle>
          <CardDescription>
            Generated from non-entitled, excess and classification-review transactions (spec OUTPUT 07). Re-generating
            preserves any reviewer decision already recorded on a finding that still applies.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating…" : "Generate / refresh findings"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          {findings.length === 0 ? (
            <p className="text-sm text-muted-foreground">No findings yet.</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>Code</Th>
                  <Th>Issue</Th>
                  <Th>Material</Th>
                  <Th>Quantity</Th>
                  <Th>Value</Th>
                  <Th>Demand</Th>
                  <Th>Status</Th>
                  {canReview && <Th>Review</Th>}
                </Tr>
              </Thead>
              <Tbody>
                {findings.map((f) => (
                  <Tr key={f.id}>
                    <Td>{f.finding_code}</Td>
                    <Td>{f.issue_type}</Td>
                    <Td className="max-w-[220px] truncate" title={f.evidence}>
                      {f.material_name ?? "—"}
                    </Td>
                    <Td>
                      {formatNumber(f.quantity)} {f.unit ?? ""}
                    </Td>
                    <Td>{formatNumber(f.value)}</Td>
                    <Td>{f.demand_amount !== null ? formatNumber(f.demand_amount) : "—"}</Td>
                    <Td>
                      <Badge tone={REVIEW_TONE[f.review_status] ?? "muted"}>{f.review_status}</Badge>
                    </Td>
                    {canReview && (
                      <Td>
                        {f.review_status !== "approved" && f.review_status !== "rejected" && (
                          <div className="flex gap-1">
                            <Button size="sm" variant="outline" disabled={busyId === f.id} onClick={() => review(f.id, "approved")}>
                              Approve
                            </Button>
                            <Button size="sm" variant="outline" disabled={busyId === f.id} onClick={() => review(f.id, "rejected")}>
                              Reject
                            </Button>
                          </div>
                        )}
                      </Td>
                    )}
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
