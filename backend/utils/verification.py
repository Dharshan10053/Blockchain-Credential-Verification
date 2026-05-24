"""
Certificate verification and issuance logic.

verify  → compares hash against blockchain; uses fuzzy matching as fallback.
issue   → adds certificate to blockchain if not already present.
"""
from __future__ import annotations
import difflib
import json
import logging

logger = logging.getLogger(__name__)

_FUZZY_THRESHOLD = 0.82  # similarity ratio for partial match


# ── Issue ─────────────────────────────────────────────────────────────────────

def issue_certificate(cert_hash: str, details: dict, blockchain) -> str:
    """Add cert to blockchain. Returns status string."""
    existing = blockchain.find_by_hash(cert_hash)
    if existing:
        logger.info("Certificate already on chain: %s", cert_hash[:12])
        return "ALREADY REGISTERED"

    block_data = {
        "certificate_id": details.get("cert_id", ""),
        "name":           details.get("name", ""),
        "course":         details.get("course", ""),
        "organization":   details.get("organization", ""),
        "date":           details.get("date", ""),
        "hash":           cert_hash,
    }
    blockchain.add_block(block_data)
    return "ISSUED SUCCESSFULLY"


# ── Verify ────────────────────────────────────────────────────────────────────

def classify_status(cert_hash: str, confidence: float, blockchain) -> dict:
    """
    Classify certificate as VERIFIED / PARTIALLY_MATCHED / FAKE.

    1. Exact hash match → VERIFIED
    2. Fuzzy similarity against stored hashes → PARTIALLY_MATCHED
    3. No match → FAKE
    """
    # 1. Exact match
    block = blockchain.find_by_hash(cert_hash)
    if block:
        return _build(
            "VERIFIED", "✓ Verified", "green",
            "Certificate hash matched exactly on the blockchain.",
            min(confidence + 10, 100),
        )

    # 2. Fuzzy match against all stored hashes
    all_hashes = blockchain.find_all_hashes()
    if all_hashes:
        best_ratio, best_hash = _best_fuzzy(cert_hash, all_hashes)
        logger.debug("Best fuzzy ratio: %.3f (hash=%s…)", best_ratio, best_hash[:8] if best_hash else "—")
        if best_ratio >= _FUZZY_THRESHOLD:
            return _build(
                "PARTIALLY_MATCHED", "~ Partial Match", "orange",
                f"Certificate is partially matched on the blockchain (similarity {best_ratio*100:.0f}%). "
                "Minor OCR differences detected.",
                round(best_ratio * 80, 1),
            )

    # 3. Not found
    return _build(
        "FAKE", "✗ Not Verified", "red",
        "Certificate was not found on the blockchain. It may be fake or unregistered.",
        0,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _best_fuzzy(target: str, candidates: set[str]) -> tuple[float, str]:
    best_ratio = 0.0
    best = ""
    for h in candidates:
        ratio = difflib.SequenceMatcher(None, target, h).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = h
    return best_ratio, best


def _build(status, label, color, message, score) -> dict:
    return {
        "status": status,
        "label": label,
        "color": color,
        "message": message,
        "confidence_score": score,
    }
