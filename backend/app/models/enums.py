from enum import StrEnum


class AuditStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    LOCKED = "locked"


class DocumentType(StrEnum):
    IMPORT_MIS = "import_mis"
    ENTITLEMENT_SHEET = "entitlement_sheet"
    ENHANCED_ENTITLEMENT = "enhanced_entitlement"
    BILL_OF_ENTRY = "bill_of_entry"
    OTHER = "other"


class Classification(StrEnum):
    RAW_MATERIAL = "raw_material"
    MACHINERY = "machinery"
    SAMPLE = "sample"
    SPARE_CONSUMABLE = "spare_consumable"
    UNKNOWN = "unknown"


class MatchStatus(StrEnum):
    UNMATCHED = "unmatched"
    SUGGESTED = "suggested"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW_REQUIRED = "review_required"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExcessStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    WITHIN_ENTITLEMENT = "within_entitlement"
    PARTIAL_EXCESS = "partial_excess"
    FULL_EXCESS = "full_excess"


class FindingIssueType(StrEnum):
    NON_ENTITLED = "non_entitled"
    EXCESS_PARTIAL = "excess_partial"
    EXCESS_FULL = "excess_full"
    DATA_QUALITY = "data_quality"
    CLASSIFICATION_REVIEW = "classification_review"
    OTHER = "other"


class FindingReviewStatus(StrEnum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
