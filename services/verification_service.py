"""
Certificate Verification Service
Handles certificate hash verification and fuzzy metadata matching.
"""
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

def _fuzzy_match_score(extracted_text: str, stored_text: str) -> float:
    if not extracted_text and not stored_text:
        return 1.0
    if not extracted_text or not stored_text:
        return 0.0
    return SequenceMatcher(None, str(extracted_text).lower(), str(stored_text).lower()).ratio()

def verify_certificate(extracted_hash: str, stored_hash: str, details: dict) -> dict:
    """
    Verify certificate authenticity using exact hash and fuzzy metadata matching.
    """
    try:
        extracted_clean = extracted_hash.strip().lower() if extracted_hash else ""
        stored_clean = stored_hash.strip().lower() if stored_hash else ""
        
        # 1. Exact Hash Match
        if extracted_clean == stored_clean:
            logger.info("Exact hash match found.")
            return {
                "status": "VALID",
                "match": True,
                "confidence_score": 98.0,
                "message": "Exact Blockchain Match",
                "explanation": "Cryptographic hash matched exactly with the immutable ledger."
            }
            
        # 2. Fuzzy Metadata Match
        # Fetch the stored metadata from DB
        from backend.database.db import get_certificate_by_hash
        record = get_certificate_by_hash(stored_clean)
        
        if record:
            name_score = _fuzzy_match_score(details.get("name"), record.get("name"))
            course_score = _fuzzy_match_score(details.get("certificate_title") or details.get("course"), record.get("course"))
            org_score = _fuzzy_match_score(details.get("issuer"), record.get("organization"))
            
            # Weighted fuzzy score (Name is most critical)
            fuzzy_ratio = (name_score * 0.5) + (course_score * 0.25) + (org_score * 0.25)
            
            if fuzzy_ratio >= 0.8:
                logger.info(f"Fuzzy match successful: {fuzzy_ratio*100:.1f}%")
                return {
                    "status": "PARTIALLY_MATCHED",
                    "match": False,
                    "confidence_score": round(fuzzy_ratio * 89.0, 1), # Max 89% for partial match
                    "message": "Partial Metadata Match",
                    "explanation": f"Hash failed, but metadata was highly similar ({fuzzy_ratio*100:.0f}% text match)."
                }
        
        # 3. No match / FAKE
        logger.info("Certificate verification failed (FAKE).")
        base_confidence = details.get("confidence_score", 0)
        # For a fake certificate, the confidence in its authenticity is very low.
        # But wait, confidence_score is used in the UI as "Extraction Confidence" or "Verification Confidence"?
        # The prompt says: "redesign the confidence scoring logic... calculate confidence dynamically... exact blockchain hash match with strong metadata can reach 95–100%, fuzzy-matched certificates should remain medium confidence only... missing critical fields should heavily reduce confidence"
        # Let's cap fake confidence to < 60%
        final_conf = min(base_confidence, 55.0)
        
        return {
            "status": "FAKE",
            "match": False,
            "confidence_score": final_conf,
            "message": "Verification Failed",
            "explanation": "Cryptographic hash did not match and metadata differed significantly."
        }
        
    except Exception as e:
        logger.error(f"Certificate verification failed: {str(e)}")
        return {
            "status": "FAKE",
            "match": False,
            "confidence_score": 0.0,
            "message": "System Error",
            "explanation": "An error occurred during blockchain verification."
        }
