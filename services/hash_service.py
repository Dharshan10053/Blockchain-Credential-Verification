"""
Certificate Hash Service
Generates SHA-256 hashes from certificate data for blockchain integration.
"""
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

def generate_certificate_hash(data: dict) -> str:
    """
    Generate SHA-256 hash from certificate data with normalization.
    
    Args:
        data (dict): Certificate data containing extracted fields
        
    Returns:
        str: SHA-256 hash hex string
    """
    try:
        # Define the field order for consistent hashing
        hash_fields = [
            "name",
            "certificate_title", 
            "issuer",
            "date",
            "certificate_id"
        ]
        
        def normalize_string(value):
            """Normalize string values for consistent hashing"""
            if value is None:
                return ""
            
            if not isinstance(value, str):
                value = str(value)
            
            # Convert to lowercase and strip whitespace
            normalized = value.lower().strip()
            
            # Remove extra whitespace and normalize spaces
            normalized = ' '.join(normalized.split())
            
            return normalized
        
        # Create ordered payload with normalized data
        payload = {}
        for field in hash_fields:
            value = data.get(field)
            payload[field] = normalize_string(value)
        
        # Convert to JSON string with sorted keys for consistency
        json_string = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        
        # Generate SHA-256 hash
        hash_object = hashlib.sha256(json_string.encode('utf-8'))
        hash_hex = hash_object.hexdigest()
        
        logger.info(f"Generated certificate hash: {hash_hex[:16]}... from {len(json_string)} chars")
        logger.debug(f"Hash payload: {payload}")
        return hash_hex
        
    except Exception as e:
        logger.error(f"Failed to generate certificate hash: {str(e)}")
        # Return a fallback hash for error cases
        fallback_data = {"error": "hash_generation_failed"}
        return hashlib.sha256(json.dumps(fallback_data).encode()).hexdigest()
