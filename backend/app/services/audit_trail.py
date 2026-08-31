"""Spec section 19 — the audit trail. Every manual decision made anywhere in the
system (mapping confirmation, match approval, finding approval, audit lock, ...)
must call `record()` so it carries old value, new value, user identity, timestamp
and an optional reason. Entries are append-only: nothing here is ever updated or
deleted."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLogEntry


def record(
    db: Session,
    *,
    user_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    audit_id: str | None = None,
    reason: str | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        audit_id=audit_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        user_id=user_id,
        reason=reason,
    )
    db.add(entry)
    db.flush()
    return entry
