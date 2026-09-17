"use client";

import { Fragment, FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/features/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, Tbody, Td, Th, Thead, Tr } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";
import { Alert } from "@/components/ui/alert";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resettingId, setResettingId] = useState<string | null>(null);

  function reload() {
    api.auth
      .listUsers()
      .then(setUsers)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load users"))
      .finally(() => setLoading(false));
  }

  useEffect(reload, []);

  return (
    <AppShell>
      <h1 className="text-xl font-semibold">Users</h1>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>All users</CardTitle>
        </CardHeader>
        <CardContent>
          {error && <Alert className="mb-3">{error}</Alert>}
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (
            <Table>
              <Thead>
                <Tr>
                  <Th>Email</Th>
                  <Th>Full name</Th>
                  <Th>Role</Th>
                  <Th>Status</Th>
                  <Th />
                </Tr>
              </Thead>
              <Tbody>
                {users.map((u) => (
                  <Fragment key={u.id}>
                    <Tr>
                      <Td>{u.email}</Td>
                      <Td>{u.full_name}</Td>
                      <Td className="uppercase">{u.role}</Td>
                      <Td>{u.is_active ? "Active" : "Disabled"}</Td>
                      <Td>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setResettingId(resettingId === u.id ? null : u.id)}
                        >
                          {resettingId === u.id ? "Cancel" : "Reset password"}
                        </Button>
                      </Td>
                    </Tr>
                    {resettingId === u.id && (
                      <Tr>
                        <Td colSpan={5}>
                          <ResetPasswordForm user={u} onDone={() => setResettingId(null)} />
                        </Td>
                      </Tr>
                    )}
                  </Fragment>
                ))}
              </Tbody>
            </Table>
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}

function ResetPasswordForm({ user, onDone }: { user: User; onDone: () => void }) {
  const [newPassword, setNewPassword] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.auth.resetPassword(user.id, newPassword, reason || undefined);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to reset password");
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <div className="flex items-center justify-between gap-4 py-2">
        <p className="text-sm text-muted-foreground">
          Password for {user.email} has been reset. Share the new password with them directly.
        </p>
        <Button variant="outline" size="sm" onClick={onDone}>
          Close
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3 py-2">
      <div>
        <Label htmlFor={`new-password-${user.id}`}>New password for {user.email}</Label>
        <Input
          id={`new-password-${user.id}`}
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          minLength={8}
          required
        />
      </div>
      <div>
        <Label htmlFor={`reason-${user.id}`}>Reason (optional)</Label>
        <Input id={`reason-${user.id}`} value={reason} onChange={(e) => setReason(e.target.value)} />
      </div>
      {error && <Alert>{error}</Alert>}
      <Button type="submit" size="sm" disabled={submitting}>
        {submitting ? "Resetting…" : "Confirm reset"}
      </Button>
    </form>
  );
}
