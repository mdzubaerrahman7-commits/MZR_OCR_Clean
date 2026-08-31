"""Spec section 18 — Bijoy/SutonnyMJ export layer.

    DATABASE / APPLICATION   (Unicode Bangla)
            |
    REPORT EXPORT LAYER
            |
    Unicode -> Bijoy-compatible conversion
            |
    Excel cell text + SutonnyMJ font
            |
    Auditor's required legacy-format report

The database and every service in this application store and operate on Unicode
Bangla exclusively (spec: 'Do not store legacy ANSI/Bijoy text as the canonical
database value'). This module is the *only* place a Unicode -> Bijoy transformation
happens, and it runs at export time, on a copy of the text, never touching stored
data.

Scope and limitation, stated up front rather than glossed over: Bijoy/SutonnyMJ is a
legacy glyph-order ANSI encoding, not a straightforward character remapping — visual
order differs from Unicode's logical (phonetic) order for pre-base vowel signs and
reph, and many consonant conjuncts (যুক্তাক্ষর) have dedicated ligature glyphs in
real Bijoy fonts that a simple table can't reproduce. This implementation handles the
structural reordering rules (pre-base matra movement, reph) and maps the base
independent vowels, consonants, vowel signs and common diacritics. Conjuncts fall
back to their hasant-joined components rather than a dedicated ligature glyph. The
spec itself flags this class of conversion as needing verification: 'The export
implementation must be tested against real Bijoy/SutonnyMJ rendering examples before
production use' — this module is that first pass, not a certified replacement for
that test.
"""

import re

HASANT = "্"
REPH_CONSONANT = "র"  # RA, forms REPH when RA + HASANT precedes another consonant

# Pre-base vowel signs: written after the consonant in Unicode logical order, but
# rendered *before* it in visual order (the order Bijoy's font glyphs assume).
PRE_BASE_VOWEL_SIGNS = {
    "ে": "†",  # E-KAR ে
    "ৈ": "‡",  # AI-KAR ৈ
}

# Base glyph table: Unicode Bangla codepoint -> Bijoy (SutonnyMJ-family ANSI) glyph.
# Independent vowels, consonants, post-base vowel signs and common diacritics.
_BASE_MAP: dict[str, str] = {
    # Independent vowels
    "অ": "A", "আ": "Av", "ই": "B", "ঈ": "C", "উ": "D",
    "ঊ": "E", "ঋ": "F", "এ": "G", "ঐ": "H", "ও": "I",
    "ঔ": "J",
    # Consonants
    "ক": "K", "খ": "L", "গ": "M", "ঘ": "N", "ঙ": "O",
    "চ": "P", "ছ": "Q", "জ": "R", "ঝ": "S", "ঞ": "T",
    "ট": "U", "ঠ": "V", "ড": "W", "ঢ": "X", "ণ": "Y",
    "ত": "Z", "থ": "_", "দ": "`", "ধ": "a", "ন": "b",
    "প": "c", "ফ": "d", "ব": "e", "ভ": "f", "ম": "g",
    "য": "h", REPH_CONSONANT: "i", "ল": "j",
    "শ": "k", "ষ": "l", "স": "m", "হ": "n",
    # Post-base vowel signs (visual order == logical order)
    "া": "v", "ি": "w", "ী": "x", "ু": "y", "ূ": "z",
    "ৃ": "„", "৉": "‰",
    # Diacritics
    "ং": "s",  # ANUSVARA
    "ঃ": "t",  # VISARGA
    "ঁ": "u",  # CHANDRABINDU
    HASANT: "&",
    # Digits
    "০": "0", "১": "1", "২": "2", "৩": "3", "৪": "4",
    "৫": "5", "৬": "6", "৭": "7", "৮": "8", "৯": "9",
}


def _reorder_pre_base_vowel_signs(text: str) -> str:
    """Move a pre-base vowel sign (e-kar/ai-kar) from after its consonant cluster
    (Unicode logical order) to before it (visual order), matching how the source
    spreadsheet's own Bijoy text would already be laid out."""

    def move_before_cluster(match: re.Match) -> str:
        cluster, vowel_sign = match.group(1), match.group(2)
        return vowel_sign + cluster

    # A "cluster" here is one or more consonants joined by HASANT, e.g. K&L, optionally
    # followed directly by the vowel sign we need to hoist in front of the whole cluster.
    pattern = re.compile(rf"((?:[ক-হ]{HASANT})*[ক-হ])([েৈ])")
    return pattern.sub(move_before_cluster, text)


def unicode_to_bijoy(text: str) -> str:
    """Convert Unicode Bangla text to a Bijoy/SutonnyMJ-compatible glyph string for
    Excel export. Non-Bangla characters (Latin, digits already in ASCII, punctuation)
    pass through unchanged."""
    if not text:
        return text

    reordered = _reorder_pre_base_vowel_signs(text)
    output_chars: list[str] = []
    for char in reordered:
        if char in PRE_BASE_VOWEL_SIGNS:
            output_chars.append(PRE_BASE_VOWEL_SIGNS[char])
        else:
            output_chars.append(_BASE_MAP.get(char, char))
    return "".join(output_chars)


def is_bangla_text(text: str) -> bool:
    return any("ঀ" <= ch <= "৿" for ch in (text or ""))
