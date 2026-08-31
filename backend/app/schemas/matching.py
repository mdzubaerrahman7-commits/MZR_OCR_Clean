from pydantic import BaseModel


class MatchBulkSuggestResult(BaseModel):
    candidates_considered: int
    suggested_count: int
    no_suggestion_count: int


class MatchConfirmRequest(BaseModel):
    decision: str  # approved | rejected | review_required
    entitlement_item_id: str | None = None
    reason: str | None = None


class ConversionBulkResult(BaseModel):
    processed_count: int
    fully_converted_count: int
    incomplete_count: int
