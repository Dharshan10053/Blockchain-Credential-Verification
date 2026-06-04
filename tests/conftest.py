"""
conftest.py — Pytest configuration for CERTAUTH test suite.
Sets up required environment variables before any app import occurs.
"""
import os
import sys

# Prepend project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment variables BEFORE importing app (app.py validates them at import time)
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("GEMINI_API_KEY", "test-api-key-not-real")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-12345")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-real")
os.environ.setdefault("BASE_URL", "http://localhost:5000")
