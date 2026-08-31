"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/features/app-shell";
import { AuditNav } from "@/components/features/audit-nav";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Alert } from "@/components/ui/alert";
import { api, ApiError } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { EntitlementGroup } from "@/lib/types";

export default function EntitlementPage() {
  const { auditId } = useParams<{ auditId: string }>();
  const [groups, setGroups] = useState<EntitlementGroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.entitlement
      .list(auditId)
      .then(setGroups)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load entitlement master"))
      .finally(() => setLoading(false));
  }, [auditId]);

  return (
    <AppShell>
      <AuditNav auditId={auditId} />
      {error && <Alert className="mb-4">{error}</Alert>}
      <Card>
        <CardHeader>
          <CardTitle>Entitlement Master</CardTitle>
          <CardDescription>
            Preserves the exact group and item sequence from the entitlement sheet (spec section 17) — never sorted
            alphabetically. Build this from Documents & Mapping after confirming the entitlement sheet&apos;s column mapping.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : groups.length === 0 ? (
            <p className="text-sm text-muted-foreground">No entitlement master built yet.</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>Group</Th>
                  <Th>SL</Th>
                  <Th>Material</Th>
                  <Th>HS Code</Th>
                  <Th>Unit</Th>
                  <Th>Annual</Th>
                  <Th>Enhanced</Th>
                  <Th>Total Entitlement</Th>
                </Tr>
              </Thead>
              <Tbody>
                {groups.map((group) =>
                  group.items.map((item, idx) => (
                    <Tr key={item.id}>
                      <Td>{idx === 0 ? group.group_name : ""}</Td>
                      <Td>{item.sequence_no}</Td>
                      <Td>{item.material_name}</Td>
                      <Td>{item.hs_code}</Td>
                      <Td>{item.entitlement_unit}</Td>
                      <Td>{formatNumber(item.annual_entitlement_qty)}</Td>
                      <Td>{formatNumber(item.enhanced_entitlement_qty)}</Td>
                      <Td className="font-medium">{formatNumber(item.total_entitlement_qty)}</Td>
                    </Tr>
                  ))
                )}
              </Tbody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
