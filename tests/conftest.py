"""
conftest.py — Pytest configuration for CERTAUTH test suite.
Sets up required environment variables before any app import occurs.
"""
import hashlib
import os
import secrets
import sys

# Prepend project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables BEFORE importing app (app.py validates them at import time)
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("GEMINI_API_KEY", "test-api-key-not-real")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-12345")
os.environ.setdefault("ENABLE_LEGACY_ADMIN_KEY", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("BASE_URL", "http://localhost:5000")

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from backend.database.db import create_api_key, create_user, init_db


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _create_admin_user(username="admin_test", password="password"):
    """Create an ADMIN user in the DB (ignores duplicate). Returns (username, password)."""
    init_db()
    create_user(username, generate_password_hash(password), "ADMIN")
    return username, password


def _create_admin_api_key(username="admin_test", password="password"):
    """Create an ADMIN user + DB-backed API key. Returns the plaintext key string."""
    from backend.database.db import get_user_by_username
    _create_admin_user(username, password)
    user = get_user_by_username(username)
    raw_key = secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    create_api_key(user["id"], key_hash)
    return raw_key


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_client():
    """Browser-session-authenticated ADMIN Flask test client."""
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.test_client() as client:
        with flask_app.app_context():
            _create_admin_user()
        # Log in through the real login endpoint
        client.post("/login", data={"username": "admin_test", "password": "password"})
        yield client


@pytest.fixture
def admin_api_key_headers():
    """
    Returns HTTP headers dict containing a valid DB-backed X-Api-Key for an ADMIN user.
    Use this fixture for all API endpoint tests that require ADMIN authentication.
    """
    flask_app.config["TESTING"] = True
    with flask_app.app_context():
        raw_key = _create_admin_api_key()
    return {"X-Api-Key": raw_key}


@pytest.fixture
def auth_headers():
    """Legacy X-Admin-Key header — use ONLY for backward-compatibility tests."""
    return {"X-Admin-Key": "test-admin-key-12345"}
