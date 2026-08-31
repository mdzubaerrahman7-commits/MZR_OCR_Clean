"""Role/permission matrix implementing spec section 20.

Role            Permission
Administrator   Manage users, companies, rules and system settings
Auditor         Upload files, map data, review exceptions, approve decisions, generate reports
Reviewer        Review findings and approve/reject
Viewer          Read-only access to assigned audits
"""

from enum import StrEnum


class Role(StrEnum):
    ADMINISTRATOR = "administrator"
    AUDITOR = "auditor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Permission(StrEnum):
    MANAGE_USERS = "manage_users"
    MANAGE_COMPANIES = "manage_companies"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"
    MANAGE_AUDITS = "manage_audits"
    UPLOAD_DOCUMENTS = "upload_documents"
    MAP_DATA = "map_data"
    RUN_AUDIT_ENGINES = "run_audit_engines"
    REVIEW_EXCEPTIONS = "review_exceptions"
    APPROVE_DECISIONS = "approve_decisions"
    APPROVE_FINDINGS = "approve_findings"
    GENERATE_REPORTS = "generate_reports"
    LOCK_AUDIT = "lock_audit"
    READ = "read"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMINISTRATOR: set(Permission),
    Role.AUDITOR: {
        Permission.MANAGE_AUDITS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.MAP_DATA,
        Permission.RUN_AUDIT_ENGINES,
        Permission.REVIEW_EXCEPTIONS,
        Permission.APPROVE_DECISIONS,
        Permission.GENERATE_REPORTS,
        Permission.LOCK_AUDIT,
        Permission.READ,
    },
    Role.REVIEWER: {
        Permission.REVIEW_EXCEPTIONS,
        Permission.APPROVE_FINDINGS,
        Permission.READ,
    },
    Role.VIEWER: {
        Permission.READ,
    },
}


def role_has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
