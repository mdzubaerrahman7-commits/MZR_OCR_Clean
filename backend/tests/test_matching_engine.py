from app.services.matching_engine import EntitlementCandidate, suggest_match

CANDIDATES = [
    EntitlementCandidate(entitlement_item_id="e1", hs_code="3902.10.00", material_name="Polypropylene Resin"),
    EntitlementCandidate(entitlement_item_id="e2", hs_code="3901.10.00", material_name="Polyethylene Resin"),
    EntitlementCandidate(entitlement_item_id="e3", hs_code="4819.10.00", material_name="Corrugated Carton"),
]


def test_exact_hs_code_match_wins() -> None:
    suggestion = suggest_match("3902.10.00", "Something unrelated text", CANDIDATES)
    assert suggestion is not None
    assert suggestion.entitlement_item_id == "e1"
    assert suggestion.method == "exact_hs_code"
    assert suggestion.confidence == 1.0


def test_falls_back_to_name_match_when_hs_not_found() -> None:
    suggestion = suggest_match("0000.00.00", "Corrugated Carton", CANDIDATES)
    assert suggestion is not None
    assert suggestion.entitlement_item_id == "e3"
    assert suggestion.method == "exact_material_name"


def test_similarity_suggestion_for_close_but_not_exact_name() -> None:
    suggestion = suggest_match("0000.00.00", "Polypropylene Resin Grade A", CANDIDATES)
    assert suggestion is not None
    assert suggestion.entitlement_item_id == "e1"
    assert suggestion.method == "similarity_suggestion"
    assert 0.6 <= suggestion.confidence < 1.0


def test_no_match_returns_none() -> None:
    suggestion = suggest_match("0000.00.00", "Completely unrelated widget", CANDIDATES)
    assert suggestion is None


def test_no_candidates_returns_none() -> None:
    assert suggest_match("3902.10.00", "Polypropylene Resin", []) is None


def test_ambiguous_hs_code_disambiguated_by_name() -> None:
    ambiguous = [
        EntitlementCandidate(entitlement_item_id="a1", hs_code="3902.10.00", material_name="Polypropylene Resin"),
        EntitlementCandidate(entitlement_item_id="a2", hs_code="3902.10.00", material_name="Polypropylene Compound"),
    ]
    suggestion = suggest_match("3902.10.00", "Polypropylene Compound", ambiguous)
    assert suggestion is not None
    assert suggestion.entitlement_item_id == "a2"
    assert suggestion.method == "exact_material_name"
