"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Alert } from "@/components/ui/alert";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { Audit, Company } from "@/lib/types";

const STATUS_TONE: Record<string, "muted" | "warning" | "success"> = {
  draft: "muted",
  in_progress: "warning",
  locked: "success",
};

export default function CompanyAuditsPage() {
  const params = useParams<{ companyId: string }>();
  const companyId = params.companyId;
  const [company, setCompany] = useState<Company | null>(null);
  const [audits, setAudits] = useState<Audit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  function reload() {
    Promise.all([api.companies.get(companyId), api.audits.list(companyId)])
      .then(([c, a]) => {
        setCompany(c);
        setAudits(a);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(reload, [companyId]);

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <div>
          <Link href="/companies" className="text-sm text-muted-foreground underline">
            ← Companies
          </Link>
          <h1 className="text-xl font-semibold">{company ? company.name : "…"} — Audits</h1>
        </div>
        <Button size="sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "New audit"}
        </Button>
      </div>

      {showForm && (
        <NewAuditForm
          companyId={companyId}
          onCreated={() => {
            setShowForm(false);
            reload();
          }}
        />
      )}

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>Audits</CardTitle>
        </CardHeader>
        <CardContent>
          {error && <Alert className="mb-3">{error}</Alert>}
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : audits.length === 0 ? (
            <p className="text-sm text-muted-foreground">No audits yet for this company.</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>Audit Code</Th>
                  <Th>Title</Th>
                  <Th>Audit Period</Th>
                  <Th>Status</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {audits.map((a) => (
                  <Tr key={a.id}>
                    <Td>{a.audit_code}</Td>
                    <Td>{a.title}</Td>
                    <Td>
                      {formatDate(a.audit_period_start)} → {formatDate(a.audit_period_end)}
                    </Td>
                    <Td>
                      <Badge tone={STATUS_TONE[a.status] ?? "muted"}>{a.status}</Badge>
                    </Td>
                    <Td>
                      <Link className="text-sm underline" href={`/audits/${a.id}`}>
                        Open
                      </Link>
                    </Td>
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

function NewAuditForm({ companyId, onCreated }: { companyId: string; onCreated: () => void }) {
  const [auditCode, setAuditCode] = useState("");
  const [title, setTitle] = useState("");
  const [auditStart, setAuditStart] = useState("");
  const [auditEnd, setAuditEnd] = useState("");
  const [entStart, setEntStart] = useState("");
  const [entEnd, setEntEnd] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.audits.create({
        company_id: companyId,
        audit_code: auditCode,
        title,
        audit_period_start: auditStart,
        audit_period_end: auditEnd,
        entitlement_period_start: entStart,
        entitlement_period_end: entEnd,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create audit");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>New audit</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="audit_code">Audit code</Label>
            <Input id="audit_code" value={auditCode} onChange={(e) => setAuditCode(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="title">Title</Label>
            <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="audit_start">Audit period start</Label>
            <Input id="audit_start" type="date" value={auditStart} onChange={(e) => setAuditStart(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="audit_end">Audit period end</Label>
            <Input id="audit_end" type="date" value={auditEnd} onChange={(e) => setAuditEnd(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="ent_start">Entitlement period start</Label>
            <Input id="ent_start" type="date" value={entStart} onChange={(e) => setEntStart(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="ent_end">Entitlement period end</Label>
            <Input id="ent_end" type="date" value={entEnd} onChange={(e) => setEntEnd(e.target.value)} required />
          </div>
          {error && (
            <div className="col-span-2">
              <Alert>{error}</Alert>
            </div>
          )}
          <div className="col-span-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create audit"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
