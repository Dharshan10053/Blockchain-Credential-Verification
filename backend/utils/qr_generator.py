"""
QR code generation for certificate verification URLs.
"""
from __future__ import annotations
import io
import os
import logging

logger = logging.getLogger(__name__)

_QR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "qrcodes")


_QR_CACHE = {}

def generate_qr(cert_hash_or_token: str, base_url: str = "http://localhost:5000", is_token: bool = False) -> str:
    """
    Generate a QR code PNG for the certificate verification URL.
    Returns the path to the saved PNG, or "" on failure.
    """
    try:
        import qrcode
        os.makedirs(_QR_DIR, exist_ok=True)
        if is_token:
            url = f"{base_url}/verify_token/{cert_hash_or_token}"
        else:
            url = f"{base_url}/certificate/{cert_hash_or_token}"
            
        out_path = os.path.join(_QR_DIR, f"{cert_hash_or_token[:16]}.png")
        if os.path.exists(out_path):
            return out_path
        img = qrcode.make(url)
        img.save(out_path)
        logger.info("QR saved: %s", out_path)
        return out_path
    except ImportError:
        logger.warning("qrcode package not installed — QR skipped.")
        return ""
    except Exception as e:
        logger.error("QR generation failed: %s", e)
        return ""


def generate_qr_base64(cert_hash_or_token: str, base_url: str = "http://localhost:5000", is_token: bool = False) -> str:
    """Return a data-URI PNG for embedding in HTML/PDF."""
    cache_key = f"{cert_hash_or_token}_{base_url}_{is_token}"
    if cache_key in _QR_CACHE:
        return _QR_CACHE[cache_key]
        
    try:
        import qrcode
        import base64
        if is_token:
            url = f"{base_url}/verify_token/{cert_hash_or_token}"
        else:
            url = f"{base_url}/certificate/{cert_hash_or_token}"
        img = qrcode.make(url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode()
        result = f"data:image/png;base64,{encoded}"
        _QR_CACHE[cache_key] = result
        return result
    except Exception as e:
        logger.error("QR base64 failed: %s", e)
        return ""
