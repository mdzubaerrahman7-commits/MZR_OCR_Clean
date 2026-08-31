"""These tests check the *structural* behavior of the Unicode->Bijoy conversion
(pass-through for non-Bangla text, pre-base vowel-sign reordering, and that Bangla
characters are actually transformed) — not byte-exact parity with a real SutonnyMJ
font, which the module's docstring explicitly defers to real-world validation
(matching the spec's own section 18 caveat)."""

from app.services.bijoy_export import is_bangla_text, unicode_to_bijoy


def test_non_bangla_text_passes_through_unchanged() -> None:
    assert unicode_to_bijoy("RAHIMAFROOZ GLOBATT LIMITED") == "RAHIMAFROOZ GLOBATT LIMITED"
    assert unicode_to_bijoy("") == ""
    assert unicode_to_bijoy("C-0001 / 2025-01-05") == "C-0001 / 2025-01-05"


def test_bangla_text_is_transformed() -> None:
    original = "বাংলাদেশ"
    converted = unicode_to_bijoy(original)
    assert converted != original


def test_pre_base_vowel_sign_is_moved_before_its_consonant() -> None:
    # কে = ক (KA) + ে (E-KAR). In visual/Bijoy order the vowel sign glyph comes first.
    converted = unicode_to_bijoy("কে")
    from app.services.bijoy_export import PRE_BASE_VOWEL_SIGNS, _BASE_MAP

    expected = PRE_BASE_VOWEL_SIGNS["ে"] + _BASE_MAP["ক"]
    assert converted == expected


def test_is_bangla_text_detection() -> None:
    assert is_bangla_text("বাংলাদেশ") is True
    assert is_bangla_text("Bangladesh") is False
    assert is_bangla_text("") is False
