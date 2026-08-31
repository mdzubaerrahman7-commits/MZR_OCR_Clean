from app.models.enums import Classification
from app.services.classification_engine import classify


def test_sample_keyword_wins() -> None:
    result, confidence = classify("Copper Wire - Sample for testing purpose", "7408.11.00", set())
    assert result == Classification.SAMPLE
    assert confidence >= 0.5


def test_spare_keyword() -> None:
    result, _confidence = classify("Machine spare part - bearing", "8483.90.00", set())
    assert result == Classification.SPARE_CONSUMABLE


def test_machinery_by_hs_chapter_when_not_in_entitlement() -> None:
    result, _confidence = classify("Injection molding machine", "8477.10.00", set())
    assert result == Classification.MACHINERY


def test_raw_material_when_hs_code_in_entitlement() -> None:
    result, confidence = classify("Polypropylene resin", "3902.10.00", {"3902.10.00"})
    assert result == Classification.RAW_MATERIAL
    assert confidence >= 0.9


def test_raw_material_by_hs_prefix_match() -> None:
    result, confidence = classify("Polypropylene resin, grade B", "3902.10.90", {"3902.10.00"})
    assert result == Classification.RAW_MATERIAL
    assert 0.5 <= confidence < 0.9


def test_unknown_when_no_signal() -> None:
    result, confidence = classify("Unidentified item", "9999.99.99", set())
    assert result == Classification.UNKNOWN
    assert confidence == 0.0


def test_entitlement_match_beats_machinery_chapter_false_positive() -> None:
    # An HS code in the 84/85 chapter range that IS on the entitlement sheet should
    # still be treated as raw material — entitlement evidence outranks the chapter heuristic.
    result, _confidence = classify("Electrical grade component", "8544.11.00", {"8544.11.00"})
    assert result == Classification.RAW_MATERIAL
