"""
Extraction-quality validation.

Sits between the existing extraction pipeline (perform_ocr -> extract_details)
and certificate issuance/verification. It answers a single question: did the
PDF/image text extraction + OCR recover enough meaningful certificate
information to act on?

Two independent signals are used, both derived from what the existing
pipeline already produces -- no new extraction logic:

  1. Text signal   -- the raw extracted text must contain a realistic amount
                      of word-like content (catches empty/near-empty output
                      and pure OCR noise from blurry or unreadable scans).
  2. Field signal  -- the fields the existing extractors parsed out of that
                      text must include a sensible minimum of identifying
                      certificate data.

The noise thresholds are deliberately tiered so imperfect-but-usable OCR is
not rejected: once the existing extractors have recovered a strong set of
identifying fields, only grossly corrupt text is refused.
"""
from __future__ import annotations

import re

# Message shown to the user when extraction is unusable.
UNREADABLE_CERTIFICATE_MESSAGE = (
    "Unable to read the certificate details. "
    "Please upload a clear, high-quality certificate."
)

# Placeholder values the existing extractors use to mean "not found".
_MISSING_VALUES = {
    "", "unknown", "not provided", "not extracted", "not found", "n/a", "na",
    "none", "null",
}

# Fields that carry identifying certificate information.
_IDENTIFYING_FIELDS = ("name", "course", "university", "date", "cert_id")

# At least one of these must be present: a bare date or serial number does
# not identify a certificate on its own.
_ANCHOR_FIELDS = ("name", "course", "university")

# --- Thresholds -----------------------------------------------------------
# Minimum raw extracted characters before the text is treated as empty.
MIN_TEXT_CHARS = 40
# Minimum number of alphabetic tokens (2+ letters) in the extracted text.
MIN_ALPHA_TOKENS = 8
# Minimum identifying fields the existing extractors must have recovered.
MIN_IDENTIFYING_FIELDS = 2
# At/above this many identifying fields the extraction counts as strong and
# only the absolute noise floor below is applied.
STRONG_IDENTIFYING_FIELDS = 3
# Standard noise thresholds (applied when the field evidence is not strong).
MIN_PLAUSIBLE_WORD_RATIO = 0.50
MIN_ALNUM_RATIO = 0.55
# Absolute noise floor (applied always, however many fields were parsed).
ABSOLUTE_MIN_PLAUSIBLE_WORD_RATIO = 0.35
ABSOLUTE_MIN_ALNUM_RATIO = 0.40

_ALPHA_TOKEN_RE = re.compile(r"[A-Za-z]{2,}")
_VOWEL_RE = re.compile(r"[AEIOUYaeiouy]")


def _is_present(value) -> bool:
    """True when a parsed field holds a real value rather than a placeholder."""
    text = str(value or "").strip()
    if len(text) < 2:
        return False
    return text.lower() not in _MISSING_VALUES


def count_identifying_fields(details: dict) -> int:
    """How many identifying certificate fields were actually recovered."""
    details = details or {}
    return sum(1 for field in _IDENTIFYING_FIELDS if _is_present(details.get(field)))


def has_identifying_anchor(details: dict) -> bool:
    """True when a recipient, course or issuing organisation was recovered."""
    details = details or {}
    return any(_is_present(details.get(field)) for field in _ANCHOR_FIELDS)


def _plausible_word_ratio(tokens) -> float:
    """
    Fraction of alphabetic tokens that look like real words.

    A token counts as plausible if it contains a vowel, or is a short
    all-caps run (acronyms such as IBM, AWS, NPTEL). OCR noise from a blurry
    scan is dominated by vowel-less consonant clusters and fails this.
    """
    if not tokens:
        return 0.0
    plausible = sum(
        1 for token in tokens
        if _VOWEL_RE.search(token) or (len(token) <= 4 and token.isupper())
    )
    return plausible / len(tokens)


def _alnum_ratio(text: str) -> float:
    """Fraction of visible characters that are letters or digits."""
    visible = [ch for ch in text if not ch.isspace()]
    if not visible:
        return 0.0
    return sum(1 for ch in visible if ch.isalnum()) / len(visible)


def assess_extraction(text: str, details: dict) -> tuple[bool, str]:
    """
    Decide whether an extraction result is usable.

    Returns (is_readable, reason). `reason` is a short machine-friendly code
    for logging only -- the user-facing text is always
    UNREADABLE_CERTIFICATE_MESSAGE.
    """
    raw = (text or "").strip()

    # 1. Empty / near-empty extraction.
    if len(raw) < MIN_TEXT_CHARS:
        return False, "empty_or_near_empty_text"

    tokens = _ALPHA_TOKEN_RE.findall(raw)
    if len(tokens) < MIN_ALPHA_TOKENS:
        return False, "too_few_words"

    plausible_ratio = _plausible_word_ratio(tokens)
    alnum_ratio = _alnum_ratio(raw)

    # 2. Absolute noise floor -- grossly corrupt text is never usable, no
    #    matter what the field extractors managed to pull out of it.
    if (
        plausible_ratio < ABSOLUTE_MIN_PLAUSIBLE_WORD_RATIO
        or alnum_ratio < ABSOLUTE_MIN_ALNUM_RATIO
    ):
        return False, "noisy_ocr_text"

    # 3. Required certificate information must be identifiable.
    field_count = count_identifying_fields(details)
    if field_count < MIN_IDENTIFYING_FIELDS or not has_identifying_anchor(details):
        return False, "insufficient_certificate_details"

    # 4. Standard noise check, skipped once the field evidence is strong so
    #    legitimate certificates are not rejected for imperfect OCR alone.
    if field_count < STRONG_IDENTIFYING_FIELDS:
        if plausible_ratio < MIN_PLAUSIBLE_WORD_RATIO:
            return False, "noisy_ocr_text"
        if alnum_ratio < MIN_ALNUM_RATIO:
            return False, "noisy_ocr_text"

    return True, "ok"


def is_readable_extraction(text: str, details: dict) -> bool:
    """Boolean convenience wrapper around assess_extraction()."""
    return assess_extraction(text, details)[0]
