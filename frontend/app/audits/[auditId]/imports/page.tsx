"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { AuditNav } from "@/components/features/audit-nav";
import { TransactionRow } from "@/components/features/transaction-row";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Th, Thead, Tr } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import { api, ApiError } from "@/lib/api";
import type { ImportTransaction } from "@/lib/types";

export default function ImportsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [transactions, setTransactions] = useState<ImportTransaction[]>([]);
  const [classificationFilter, setClassificationFilter] = useState("");
  const [reviewOnly, setReviewOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  function reload() {
    api.imports
      .list(auditId, { classification: classificationFilter || undefined, review_required: reviewOnly || undefined })
      .then(setTransactions)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load transactions"));
  }

  useEffect(reload, [auditId, classificationFilter, reviewOnly]);

  async function runEngine(name: string, action: () => Promise<unknown>) {
    setBusyAction(name);
    setError(null);
    setMessage(null);
    try {
      const result = await action();
      setMessage(`${name}: ${JSON.stringify(result)}`);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `${name} failed`);
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <AppShell>
      <AuditNav auditId={auditId} />
      {error && <Alert className="mb-4">{error}</Alert>}
      {message && <p className="mb-4 truncate rounded-md bg-muted p-3 text-sm">{message}</p>}

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Run audit engines</CardTitle>
          <CardDescription>Run in order after parsing the Import MIS: Classify → Match → Convert → Detect Excess.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" disabled={!!busyAction} onClick={() => runEngine("Classify", () => api.rules.classify(auditId))}>
            Re-classify
          </Button>
          <Button size="sm" variant="outline" disabled={!!busyAction} onClick={() => runEngine("Match", () => api.rules.matchEntitlements(auditId))}>
            Match to entitlement
          </Button>
          <Button size="sm" variant="outline" disabled={!!busyAction} onClick={() => runEngine("Convert", () => api.rules.calculateConversions(auditId))}>
            Calculate conversions
          </Button>
          <Button size="sm" variant="outline" disabled={!!busyAction} onClick={() => runEngine("Detect excess", () => api.rules.detectExcess(auditId))}>
            Detect excess
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Import transactions</CardTitle>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Select value={classificationFilter} onChange={(e) => setClassificationFilter(e.target.value)} className="w-40">
                <option value="">All classifications</option>
                <option value="raw_material">Raw Material</option>
                <option value="machinery">Machinery</option>
                <option value="sample">Sample</option>
                <option value="spare_consumable">Spare/Consumable</option>
                <option value="unknown">Unknown</option>
              </Select>
              <label className="flex items-center gap-1">
                <input type="checkbox" checked={reviewOnly} onChange={(e) => setReviewOnly(e.target.checked)} />
                Review required only
              </label>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No transactions match the current filters.</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>B/E No</Th>
                  <Th>B/E Date</Th>
                  <Th>Description</Th>
                  <Th>HS Code</Th>
                  <Th>Qty</Th>
                  <Th>Classification</Th>
                  <Th>Match</Th>
                  <Th>Entitlement Qty</Th>
                  <Th>USD Value</Th>
                  <Th>Excess</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {transactions.map((txn) => (
                  <TransactionRow key={txn.id} auditId={auditId} txn={txn} onChanged={reload} />
                ))}
              </Tbody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
