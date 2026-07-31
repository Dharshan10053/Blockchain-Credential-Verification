"""
Certificate Ledger Storage Service
Handles simulated blockchain storage for certificate hashes.
"""
import os
import json
import logging
from threading import Lock

logger = logging.getLogger(__name__)

class LedgerService:
    def __init__(self, ledger_path: str = None):
        """
        Initialize the ledger service.
        
        Args:
            ledger_path (str): Path to the ledger JSON file
        """
        if ledger_path is None:
            # Default path relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ledger_path = os.path.join(base_dir, "data", "ledger.json")
        
        self.ledger_path = ledger_path
        self._lock = Lock()
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
        
        # Initialize ledger file if it doesn't exist
        self._ensure_ledger_exists()
    
    def _ensure_ledger_exists(self):
        """Ensure the ledger file exists with proper structure."""
        try:
            if not os.path.exists(self.ledger_path):
                with open(self.ledger_path, 'w') as f:
                    json.dump({}, f, indent=2)
                logger.info(f"Created new ledger file: {self.ledger_path}")
        except Exception as e:
            logger.error(f"Failed to create ledger file: {e}")
            raise
    
    def _load_ledger(self) -> dict:
        """Load the ledger data from file."""
        try:
            with self._lock:
                with open(self.ledger_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load ledger: {e}")
            return {}
    
    def _save_ledger(self, ledger_data: dict):
        """Save ledger data to file."""
        try:
            with self._lock:
                with open(self.ledger_path, 'w') as f:
                    json.dump(ledger_data, f, indent=2)
                logger.debug(f"Saved ledger data to {self.ledger_path}")
        except Exception as e:
            logger.error(f"Failed to save ledger: {e}")
            raise
    
    def store_certificate(self, certificate_id: str, cert_hash: str) -> bool:
        """
        Store a certificate hash in the ledger.
        
        Args:
            certificate_id (str): Unique certificate identifier
            cert_hash (str): SHA-256 hash of certificate data
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            ledger = self._load_ledger()
            ledger[certificate_id] = cert_hash
            self._save_ledger(ledger)
            
            logger.info(f"Stored certificate: {certificate_id} -> {cert_hash[:16]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store certificate {certificate_id}: {e}")
            return False
    
    def get_stored_hash(self, certificate_id: str) -> str:
        """
        Retrieve stored hash for a certificate.
        
        Args:
            certificate_id (str): Unique certificate identifier
            
        Returns:
            str: Stored hash or None if not found
        """
        try:
            ledger = self._load_ledger()
            stored_hash = ledger.get(certificate_id)
            
            if stored_hash:
                logger.info(f"Retrieved stored hash for {certificate_id}: {stored_hash[:16]}...")
            else:
                logger.info(f"No stored hash found for certificate: {certificate_id}")
            
            return stored_hash
            
        except Exception as e:
            logger.error(f"Failed to retrieve stored hash for {certificate_id}: {e}")
            return None
    
    def certificate_exists(self, certificate_id: str) -> bool:
        """
        Check if a certificate exists in the ledger.
        
        Args:
            certificate_id (str): Unique certificate identifier
            
        Returns:
            bool: True if certificate exists, False otherwise
        """
        try:
            ledger = self._load_ledger()
            exists = certificate_id in ledger
            logger.debug(f"Certificate {certificate_id} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check certificate existence for {certificate_id}: {e}")
            return False
    
    def get_all_certificates(self) -> dict:
        """
        Get all certificates from the ledger.
        
        Returns:
            dict: All certificate_id -> hash mappings
        """
        try:
            ledger = self._load_ledger()
            logger.info(f"Retrieved {len(ledger)} certificates from ledger")
            return ledger
        except Exception as e:
            logger.error(f"Failed to retrieve all certificates: {e}")
            return {}

# Global instance for easy access
ledger_service = LedgerService()
