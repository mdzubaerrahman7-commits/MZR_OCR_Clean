"use client";

import { useState } from "react";
import { Td, Tr } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/utils";
import type { EntitlementItem, ImportTransaction } from "@/lib/types";

const CLASSIFICATION_TONE: Record<string, "muted" | "warning" | "success" | "danger"> = {
  raw_material: "success",
  machinery: "muted",
  sample: "muted",
  spare_consumable: "muted",
  unknown: "warning",
};

const MATCH_TONE: Record<string, "muted" | "warning" | "success" | "danger"> = {
  unmatched: "muted",
  suggested: "warning",
  approved: "success",
  rejected: "danger",
  review_required: "danger",
};

const EXCESS_TONE: Record<string, "muted" | "warning" | "success" | "danger"> = {
  not_applicable: "muted",
  within_entitlement: "success",
  partial_excess: "warning",
  full_excess: "danger",
};

const CLASSIFICATIONS = ["raw_material", "machinery", "sample", "spare_consumable", "unknown"];

export function TransactionRow({ auditId, txn, onChanged }: { auditId: string; txn: ImportTransaction; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [newClassification, setNewClassification] = useState(txn.classification);
  const [reason, setReason] = useState("");
  const [candidates, setCandidates] = useState<EntitlementItem[] | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState("");

  async function saveOverride() {
    setBusy(true);
    setError(null);
    try {
      await api.imports.overrideClassification(auditId, txn.id, newClassification, reason || "Manual auditor review");
      setOverrideOpen(false);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to override classification");
    } finally {
      setBusy(false);
    }
  }

  async function loadCandidates() {
    try {
      const result = await api.imports.matchCandidates(auditId, txn.id);
      setCandidates(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load candidates");
    }
  }

  async function decide(decision: "approved" | "rejected" | "review_required") {
    setBusy(true);
    setError(null);
    try {
      await api.imports.confirmMatch(auditId, txn.id, decision, selectedCandidate || undefined);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record match decision");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Tr>
        <Td>{txn.be_number}</Td>
        <Td>{formatDate(txn.be_date)}</Td>
        <Td className="max-w-[220px] truncate" title={txn.item_description}>
          {txn.item_description}
        </Td>
        <Td>{txn.hs_code}</Td>
        <Td>
          {formatNumber(txn.declared_quantity)} {txn.declared_unit}
        </Td>
        <Td>
          <Badge tone={CLASSIFICATION_TONE[txn.classification]}>{txn.classification}</Badge>{" "}
          <button className="text-xs underline" onClick={() => setOverrideOpen((v) => !v)}>
            edit
          </button>
        </Td>
        <Td>
          <Badge tone={MATCH_TONE[txn.match_status]}>{txn.match_status}</Badge>
        </Td>
        <Td>{txn.entitlement_quantity ? `${formatNumber(txn.entitlement_quantity)} ${txn.entitlement_unit ?? ""}` : "—"}</Td>
        <Td>{formatNumber(txn.usd_value)}</Td>
        <Td>
          <Badge tone={EXCESS_TONE[txn.excess_status]}>{txn.excess_status}</Badge>
        </Td>
        <Td>
          {(txn.match_status === "suggested" || txn.match_status === "review_required") && (
            <div className="flex flex-col gap-1">
              <div className="flex gap-1">
                <Button size="sm" variant="outline" disabled={busy} onClick={() => decide("approved")}>
                  Approve
                </Button>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => decide("rejected")}>
                  Reject
                </Button>
              </div>
              {!candidates && (
                <button className="text-xs underline" onClick={loadCandidates}>
                  Pick a different entitlement item…
                </button>
              )}
              {candidates && (
                <Select value={selectedCandidate} onChange={(e) => setSelectedCandidate(e.target.value)}>
                  <option value="">— current suggestion —</option>
                  {candidates.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.material_name} ({c.hs_code})
                    </option>
                  ))}
                </Select>
              )}
            </div>
          )}
        </Td>
      </Tr>
      {overrideOpen && (
        <Tr>
          <Td colSpan={11}>
            <div className="flex items-end gap-2 rounded-md bg-muted p-2">
              <div>
                <label className="mb-1 block text-xs font-medium">New classification</label>
                <Select value={newClassification} onChange={(e) => setNewClassification(e.target.value as typeof newClassification)}>
                  {CLASSIFICATIONS.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium">Reason</label>
                <input
                  className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Why is this being reclassified?"
                />
              </div>
              <Button size="sm" disabled={busy} onClick={saveOverride}>
                Save
              </Button>
            </div>
          </Td>
        </Tr>
      )}
      {error && (
        <Tr>
          <Td colSpan={11} className="text-xs text-destructive">
            {error}
          </Td>
        </Tr>
      )}
    </>
  );
}
