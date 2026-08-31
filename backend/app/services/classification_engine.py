"""M05 — Import Classification Engine (spec section 15).

Deterministic, evidence-based rules — no ML/AI here, so every classification is
reproducible from (item_description, hs_code, entitlement_hs_codes) alone (spec
section 24: 'every calculated result must be reproducible'). Anything the rules
can't confidently place is Unknown, which is a real classification, not an error:
it routes the row to mandatory auditor review instead of guessing (spec section 3).
"""

from app.models.enums import Classification

MACHINERY_HS_CHAPTERS = {"84", "85"}  # mechanical appliances / electrical machinery & equipment

SAMPLE_KEYWORDS = ("sample", "free sample", "not for sale", "for testing purpose")
SPARE_KEYWORDS = ("spare part", "spares", "consumable", "lubricant", "grease", "maintenance item", "stationery")
MACHINERY_KEYWORDS = ("machine", "machinery", "equipment", "generator", "compressor", "plant & machinery")

# Confidence below this is treated the same as no match: forced to Unknown/review.
CONFIDENCE_THRESHOLD = 0.5


def _hs_chapter(hs_code: str) -> str:
    digits = "".join(ch for ch in hs_code if ch.isdigit())
    return digits[:2]


def _hs_matches_entitlement(hs_code: str, entitlement_hs_codes: set[str]) -> float:
    if not hs_code:
        return 0.0
    if hs_code in entitlement_hs_codes:
        return 0.95
    hs_prefix = "".join(ch for ch in hs_code if ch.isdigit())[:6]
    if not hs_prefix:
        return 0.0
    for candidate in entitlement_hs_codes:
        candidate_prefix = "".join(ch for ch in candidate if ch.isdigit())[:6]
        if candidate_prefix and candidate_prefix == hs_prefix:
            return 0.75
    return 0.0


def classify(
    item_description: str, hs_code: str, entitlement_hs_codes: set[str]
) -> tuple[Classification, float]:
    description = (item_description or "").lower()
    hs_code = hs_code or ""

    if any(keyword in description for keyword in SAMPLE_KEYWORDS):
        return Classification.SAMPLE, 0.9

    if any(keyword in description for keyword in SPARE_KEYWORDS):
        return Classification.SPARE_CONSUMABLE, 0.85

    chapter = _hs_chapter(hs_code)
    entitlement_confidence = _hs_matches_entitlement(hs_code, entitlement_hs_codes)

    if chapter in MACHINERY_HS_CHAPTERS and entitlement_confidence < CONFIDENCE_THRESHOLD:
        return Classification.MACHINERY, 0.8

    if any(keyword in description for keyword in MACHINERY_KEYWORDS) and entitlement_confidence < CONFIDENCE_THRESHOLD:
        return Classification.MACHINERY, 0.7

    if entitlement_confidence >= CONFIDENCE_THRESHOLD:
        return Classification.RAW_MATERIAL, entitlement_confidence

    return Classification.UNKNOWN, 0.0
