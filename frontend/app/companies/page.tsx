"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/features/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import { useAuth, hasPermissionHint } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import type { Company } from "@/lib/types";

export default function CompaniesPage() {
  const { user } = useAuth();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  function reload() {
    api.companies
      .list()
      .then(setCompanies)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load companies"))
      .finally(() => setLoading(false));
  }

  useEffect(reload, []);

  const canManage = hasPermissionHint(user?.role, ["administrator"]);

  return (
    <AppShell>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Companies</h1>
        {canManage && (
          <Button onClick={() => setShowForm((v) => !v)} size="sm">
            {showForm ? "Cancel" : "New company"}
          </Button>
        )}
      </div>

      {showForm && <NewCompanyForm onCreated={() => { setShowForm(false); reload(); }} />}

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>All companies</CardTitle>
        </CardHeader>
        <CardContent>
          {error && <Alert className="mb-3">{error}</Alert>}
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : companies.length === 0 ? (
            <p className="text-sm text-muted-foreground">No companies yet.</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>Name</Th>
                  <Th>BIN</Th>
                  <Th>Bond License</Th>
                  <Th>Facility Type</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {companies.map((c) => (
                  <Tr key={c.id}>
                    <Td>{c.name}</Td>
                    <Td>{c.bin_number}</Td>
                    <Td>{c.bond_license_number}</Td>
                    <Td>{c.facility_type}</Td>
                    <Td>
                      <Link className="text-sm underline" href={`/companies/${c.id}/audits`}>
                        View audits
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

function NewCompanyForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [bin, setBin] = useState("");
  const [license, setLicense] = useState("");
  const [facilityType, setFacilityType] = useState("bonded_warehouse");
  const [address, setAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.companies.create({ name, bin_number: bin, bond_license_number: license, facility_type: facilityType, address });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create company");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>New company</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <Label htmlFor="name">Company name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="bin">BIN</Label>
            <Input id="bin" value={bin} onChange={(e) => setBin(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="license">Bond license number</Label>
            <Input id="license" value={license} onChange={(e) => setLicense(e.target.value)} required />
          </div>
          <div>
            <Label htmlFor="facility">Facility type</Label>
            <Input id="facility" value={facilityType} onChange={(e) => setFacilityType(e.target.value)} />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="address">Address</Label>
            <Input id="address" value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>
          {error && (
            <div className="sm:col-span-2">
              <Alert>{error}</Alert>
            </div>
          )}
          <div className="sm:col-span-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create company"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
