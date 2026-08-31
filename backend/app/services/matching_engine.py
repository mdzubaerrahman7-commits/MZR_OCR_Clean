"""M06 — Entitlement Matching Engine (spec section 10).

Pipeline: exact HS code -> exact/normalized material name -> similarity suggestion.
Every path here produces, at most, a *suggestion* (MatchStatus.SUGGESTED) — never
MatchStatus.APPROVED. Only an explicit auditor confirmation (the router's
`confirm_match` endpoint) can set APPROVED/REJECTED/REVIEW_REQUIRED, per spec
section 10's 'Never automatically approve a fuzzy AI match as a final audit
decision' and section 24's 'Never allow AI suggestions to bypass auditor approval.'
"""

import difflib
from dataclasses import dataclass

SIMILARITY_CUTOFF = 0.6


@dataclass(frozen=True)
class EntitlementCandidate:
    entitlement_item_id: str
    hs_code: str
    material_name: str


@dataclass
class MatchSuggestion:
    entitlement_item_id: str
    method: str  # exact_hs_code | exact_material_name | similarity_suggestion
    confidence: float
    evidence: str


def _normalize_hs(hs_code: str) -> str:
    return "".join(ch for ch in (hs_code or "") if ch.isalnum()).upper()


def _normalize_name(name: str) -> str:
    return " ".join((name or "").lower().split())


def suggest_match(
    hs_code: str, item_description: str, candidates: list[EntitlementCandidate]
) -> MatchSuggestion | None:
    if not candidates:
        return None

    normalized_hs = _normalize_hs(hs_code)
    hs_matches = [c for c in candidates if _normalize_hs(c.hs_code) == normalized_hs and normalized_hs]
    if len(hs_matches) == 1:
        match = hs_matches[0]
        return MatchSuggestion(
            entitlement_item_id=match.entitlement_item_id,
            method="exact_hs_code",
            confidence=1.0,
            evidence=f"Exact HS code match: import HS '{hs_code}' == entitlement HS '{match.hs_code}' ({match.material_name})",
        )

    # Multiple entitlement items share this HS code (or none did) — fall through to
    # name matching, scoped to the HS-ambiguous set when there is one, else all candidates.
    search_pool = hs_matches if hs_matches else candidates
    normalized_description = _normalize_name(item_description)

    exact_name_matches = [c for c in search_pool if _normalize_name(c.material_name) == normalized_description]
    if len(exact_name_matches) == 1:
        match = exact_name_matches[0]
        note = " (disambiguated among items sharing this HS code)" if hs_matches else ""
        return MatchSuggestion(
            entitlement_item_id=match.entitlement_item_id,
            method="exact_material_name",
            confidence=0.9,
            evidence=f"Exact material name match: '{item_description}' == '{match.material_name}'{note}",
        )

    name_by_candidate = {c.entitlement_item_id: _normalize_name(c.material_name) for c in search_pool}
    best_id: str | None = None
    best_ratio = 0.0
    for entitlement_item_id, normalized_name in name_by_candidate.items():
        ratio = difflib.SequenceMatcher(None, normalized_description, normalized_name).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_id = entitlement_item_id

    if best_id is not None and best_ratio >= SIMILARITY_CUTOFF:
        match = next(c for c in search_pool if c.entitlement_item_id == best_id)
        return MatchSuggestion(
            entitlement_item_id=match.entitlement_item_id,
            method="similarity_suggestion",
            confidence=round(best_ratio, 4),
            evidence=f"Similarity suggestion: '{item_description}' ~ '{match.material_name}' (ratio={best_ratio:.2f})",
        )

    return None
