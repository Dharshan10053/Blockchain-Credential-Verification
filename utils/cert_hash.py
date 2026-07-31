"""
Canonical certificate representation and hashing for verification.

Normalizes extracted fields so that minor OCR differences (spaces, case for
non-name fields) still produce the same hash when issuing and verifying.
"""

import hashlib
import re


def _normalize_field(value: str, preserve_case: bool = False) -> str:
    """Collapse whitespace and strip. Optionally lowercase for consistency."""
    if not value or value == "Unknown":
        return value
    s = re.sub(r"\s+", " ", value.strip())
    return s if preserve_case else s.strip()


def build_canonical_payload(
    name: str,
    course: str,
    date: str,
    cert_id: str,
    *,
    normalize_name_case: bool = False,
) -> str:
    """
    Build a deterministic string from certificate fields for hashing.
    Uses a single separator so the format is stable across layouts.
    """
    name = _normalize_field(name, preserve_case=not normalize_name_case)
    course = _normalize_field(course, preserve_case=False)
    date = _normalize_field(date, preserve_case=False)
    cert_id = _normalize_field(cert_id, preserve_case=False)
    return f"{name}|{course}|{date}|{cert_id}"


def generate_cert_hash(
    name: str,
    course: str,
    date: str,
    cert_id: str,
    **kwargs,
) -> str:
    """SHA-256 hash of the canonical payload. Use same args when issuing and verifying."""
    payload = build_canonical_payload(name, course, date, cert_id, **kwargs)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
