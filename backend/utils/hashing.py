"""
Deterministic SHA-256 hash from certificate details dict.
Field order is fixed so the same details always yield the same hash.
"""
from __future__ import annotations
import hashlib
import json


_HASH_FIELDS = ("name", "course", "organization", "date", "cert_id")


def generate_hash_from_details(details: dict) -> str:
    payload = {k: (details.get(k) or "").strip().lower() for k in _HASH_FIELDS}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()
