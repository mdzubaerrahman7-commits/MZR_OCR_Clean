"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { AuditNav } from "@/components/features/audit-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Audit } from "@/lib/types";

const WORKFLOW_STEPS = [
  "Create Company", "Create Audit", "Set Audit Period", "Upload Entitlement Sheet", "Upload Import MIS",
  "Review Sheet/Header Mapping", "Filter Audit Period Transactions", "Classify Imports", "Build Entitlement Master",
  "Match Raw Materials to Entitlement", "Apply B/E Quantity & Currency Evidence", "Detect Non-Entitled Imports",
  "Detect Excess Imports Chronologically", "Review Exceptions", "Approve Findings", "Generate Excel Outputs",
  "Lock / Archive Audit Version",
];

export default function AuditOverviewPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [audit, setAudit] = useState<Audit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [locking, setLocking] = useState(false);

  function reload() {
    api.audits
      .get(auditId)
      .then(setAudit)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load audit"));
  }

  useEffect(reload, [auditId]);

  async function handleLock() {
    if (!confirm("Locking archives this audit's evidence and results permanently and cannot be undone. Continue?")) return;
    setLocking(true);
    try {
      await api.audits.lock(auditId);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to lock audit");
    } finally {
      setLocking(false);
    }
  }

  return (
    <AppShell>
      <AuditNav auditId={auditId} />
      {error && <Alert className="mb-4">{error}</Alert>}
      {audit && (
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle>
                    {audit.audit_code} — {audit.title}
                  </CardTitle>
                  <CardDescription>
                    Audit period {formatDate(audit.audit_period_start)} → {formatDate(audit.audit_period_end)} · Entitlement period{" "}
                    {formatDate(audit.entitlement_period_start)} → {formatDate(audit.entitlement_period_end)}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-3">
                  <Badge tone={audit.status === "locked" ? "success" : "warning"}>{audit.status}</Badge>
                  {audit.status !== "locked" && (
                    <Button size="sm" variant="destructive" onClick={handleLock} disabled={locking}>
                      {locking ? "Locking…" : "Lock / Archive Audit"}
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Workflow (spec section 22)</CardTitle>
              <CardDescription>Follow the tabs above in this order.</CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="grid grid-cols-1 gap-x-8 gap-y-1 text-sm text-muted-foreground sm:grid-cols-2">
                {WORKFLOW_STEPS.map((step, i) => (
                  <li key={step}>
                    {i + 1}. {step}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Link href={`/audits/${auditId}/documents`}>
              <Card className="cursor-pointer hover:bg-muted"><CardContent className="p-4">Upload & map documents</CardContent></Card>
            </Link>
            <Link href={`/audits/${auditId}/imports`}>
              <Card className="cursor-pointer hover:bg-muted"><CardContent className="p-4">Review imports & matching</CardContent></Card>
            </Link>
            <Link href={`/audits/${auditId}/reports`}>
              <Card className="cursor-pointer hover:bg-muted"><CardContent className="p-4">Generate reports</CardContent></Card>
            </Link>
          </div>
        </div>
      )}
    </AppShell>
  );
}
