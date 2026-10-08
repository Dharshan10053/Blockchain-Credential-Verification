"""Evidence-based extraction confidence for certificate verification."""
from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Iterable, Mapping

_FIELDS = ("name", "course", "university", "date", "cert_id")
_MISSING = {
    "", "unknown", "not provided", "not extracted", "not found",
    "n/a", "na", "none", "null",
}
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _present(value) -> bool:
    text = str(value or "").strip()
    return len(text) > 1 and text.casefold() not in _MISSING


def _valid_ocr_words(ocr_data: Iterable[Mapping]) -> list[tuple[str, float]]:
    words = []
    for item in ocr_data or ():
        text = str(item.get("text") or "").strip()
        try:
            confidence = float(item.get("conf"))
        except (TypeError, ValueError):
            continue
        if not text or not math.isfinite(confidence) or not 0 <= confidence <= 100:
            continue
        words.extend(
            (token.casefold(), confidence)
            for token in _TOKEN_RE.findall(text)
        )
    return words


def _token_match(target: str, candidate: str) -> bool:
    if target == candidate:
        return True
    if min(len(target), len(candidate)) < 4:
        return False
    return SequenceMatcher(None, target, candidate).ratio() >= 0.8


def calculate_verification_confidence(
    details: Mapping, ocr_data: Iterable[Mapping]
) -> dict:
    """Score extraction evidence without influencing the blockchain decision."""
    details = details or {}
    words = _valid_ocr_words(ocr_data)
    ocr_available = bool(words)
    completeness = sum(_present(details.get(field)) for field in _FIELDS) / len(_FIELDS) * 100

    field_confidence = {}
    field_coverage = []
    for field in _FIELDS:
        value = details.get(field)
        if not ocr_available:
            field_confidence[field] = None
            continue
        if not _present(value):
            field_confidence[field] = 0.0
            continue

        targets = [token.casefold() for token in _TOKEN_RE.findall(str(value))]
        available = list(words)
        matched_confidences = []
        matched_tokens = 0
        for target in targets:
            match_index = next(
                (
                    index for index, (candidate, _) in enumerate(available)
                    if _token_match(target, candidate)
                ),
                None,
            )
            if match_index is None:
                matched_confidences.append(0.0)
            else:
                _, confidence = available.pop(match_index)
                matched_confidences.append(confidence)
                matched_tokens += 1
        field_confidence[field] = (
            sum(matched_confidences) / len(targets) if targets else 0.0
        )
        field_coverage.append(matched_tokens / len(targets) if targets else 0.0)

    consistency_checks = []
    consistency_signals = []
    if ocr_available:
        field_support = (
            sum(field_coverage) / len(field_coverage) * 100
            if field_coverage else 0.0
        )
        consistency_signals.append(field_support)
        consistency_checks.append(f"OCR field support: {field_support:.0f}%")
    else:
        consistency_checks.append("OCR word confidence unavailable")

    date = str(details.get("date") or "")
    year = str(details.get("year") or "")
    date_years = _YEAR_RE.findall(date)
    supplied_years = _YEAR_RE.findall(year)
    if date_years and supplied_years:
        date_consistent = date_years[-1] == supplied_years[-1]
        consistency_signals.append(100.0 if date_consistent else 0.0)
        consistency_checks.append(
            "Date/year consistency: " + ("pass" if date_consistent else "conflict")
        )

    consistency = (
        sum(consistency_signals) / len(consistency_signals)
        if consistency_signals else None
    )

    if ocr_available:
        ocr_score = sum(field_confidence[field] or 0.0 for field in _FIELDS) / len(_FIELDS)
        score = 0.60 * ocr_score + 0.25 * completeness + 0.15 * (consistency or 0.0)
        formula = "60% field OCR confidence + 25% extraction completeness + 15% consistency"
    elif consistency is not None:
        score = min(75.0, 0.625 * completeness + 0.375 * consistency)
        formula = (
            "OCR confidence unavailable; 62.5% completeness + 37.5% consistency, "
            "capped at 75%"
        )
    else:
        score = min(75.0, completeness)
        formula = "OCR confidence unavailable; completeness-only score capped at 75%"

    return {
        "confidence_score": round(max(0.0, min(100.0, score)), 1),
        "field_confidence": field_confidence,
        "completeness_score": round(completeness, 1),
        "fields_found": int(completeness / 100 * len(_FIELDS)),
        "field_count": len(_FIELDS),
        "consistency_score": round(consistency, 1) if consistency is not None else None,
        "consistency_checks": consistency_checks,
        "ocr_confidence_available": ocr_available,
        "formula": formula,
    }
