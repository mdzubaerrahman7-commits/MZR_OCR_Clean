"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { AuditNav } from "@/components/features/audit-nav";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Alert } from "@/components/ui/alert";
import { api, ApiError } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { ExceptionDashboard, ImportTransaction } from "@/lib/types";

const CONTROLS: { key: keyof ExceptionDashboard; label: string }[] = [
  { key: "non_entitled_count", label: "Non-entitled imports" },
  { key: "review_required_match_count", label: "Matches awaiting review" },
  { key: "unknown_classification_count", label: "Unknown classification" },
  { key: "partial_excess_count", label: "Partial excess" },
  { key: "full_excess_count", label: "Full excess" },
  { key: "conversion_incomplete_count", label: "Conversion incomplete" },
];

export default function ExceptionsPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [data, setData] = useState<ExceptionDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.rules
      .exceptions(auditId)
      .then(setData)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load exception dashboard"));
  }, [auditId]);

  return (
    <AppShell>
      <AuditNav auditId={auditId} />
      {error && <Alert className="mb-4">{error}</Alert>}
      {data && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-3 gap-4 md:grid-cols-6">
            {CONTROLS.map((c) => (
              <Card key={c.key}>
                <CardContent className="p-4">
                  <div className="text-2xl font-semibold">{data[c.key] as number}</div>
                  <div className="text-xs text-muted-foreground">{c.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>

          <ExceptionTable title="Non-entitled imports" rows={data.non_entitled_transactions} />
          <ExceptionTable title="Excess (partial/full)" rows={data.excess_transactions} showExcess />
          <ExceptionTable title="Matches awaiting review" rows={data.review_required_transactions} />
          <ExceptionTable title="Conversion incomplete" rows={data.conversion_incomplete_transactions} />
        </div>
      )}
    </AppShell>
  );
}

function ExceptionTable({ title, rows, showExcess }: { title: string; rows: ImportTransaction[]; showExcess?: boolean }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {title} ({rows.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">None.</p>
        ) : (
          <Table>
            <Thead>
              <Tr>
                <Th>B/E No</Th>
                <Th>Material</Th>
                <Th>HS Code</Th>
                <Th>Qty</Th>
                {showExcess && <Th>Excess Qty</Th>}
              </Tr>
            </Thead>
            <Tbody>
              {rows.map((t) => (
                <Tr key={t.id}>
                  <Td>{t.be_number}</Td>
                  <Td className="max-w-[260px] truncate">{t.item_description}</Td>
                  <Td>{t.hs_code}</Td>
                  <Td>
                    {formatNumber(t.declared_quantity)} {t.declared_unit}
                  </Td>
                  {showExcess && <Td>{formatNumber(t.excess_quantity)}</Td>}
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
