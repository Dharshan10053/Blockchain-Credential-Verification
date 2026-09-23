"""
test_security.py — Security regression tests for CERTAUTH.
Tests: headers, auth, input validation, error handlers, rate limiting.
"""
import os
import sys
import hashlib
import secrets
from urllib.parse import quote

# conftest.py handles env var setup before this runs
from app import app, limiter
from backend.database.db import (
    create_api_key,
    create_user,
    get_user_by_username,
    get_user_by_api_key_hash,
    init_db,
    revoke_api_key,
    upsert_certificate,
)
from werkzeug.security import generate_password_hash


class TestSecurityHeaders:
    """Verify all required security headers are present on responses."""

    def setup_method(self):
        self.client = app.test_client()

    def test_x_content_type_options(self):
        r = self.client.get("/")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self):
        r = self.client.get("/")
        assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_referrer_policy(self):
        r = self.client.get("/")
        assert "Referrer-Policy" in r.headers

    def test_permissions_policy(self):
        r = self.client.get("/")
        assert "Permissions-Policy" in r.headers

    def test_content_security_policy(self):
        r = self.client.get("/")
        assert "Content-Security-Policy" in r.headers

    def test_hsts(self):
        r = self.client.get("/")
        assert "Strict-Transport-Security" in r.headers

    def test_no_xss_protection_header(self):
        """X-XSS-Protection is deprecated and removed — should NOT be present."""
        r = self.client.get("/")
        assert "X-XSS-Protection" not in r.headers


class TestInputValidation:
    """Verify that malformed input params are rejected with 400, not 500."""

    def setup_method(self):
        self.client = app.test_client()

    def test_invalid_cert_hash_in_certificate_view(self):
        """A non-hex or short hash should return 400 not 500."""
        r = self.client.get("/certificate/not-a-valid-hash")
        assert r.status_code == 400

    def test_sql_injection_in_cert_hash(self):
        r = self.client.get("/certificate/' OR 1=1 --")
        assert r.status_code in [400, 404]  # Not 500

    def test_invalid_token_in_verify_token(self):
        r = self.client.get("/verify_token/not-a-valid-uuid")
        assert r.status_code == 400

    def test_invalid_hash_in_report(self):
        r = self.client.get("/report/badcerth")
        assert r.status_code == 400

    def test_certificate_lookup_does_not_expose_verification_token(self):
        cert_hash = "e" * 64
        token = upsert_certificate(
            cert_hash,
            {
                "name": "Public Holder",
                "certificate_id": "PUBLIC-001",
                "course": "Public Course",
            },
            action="ISSUE",
        )

        response = self.client.get(f"/certificate/{cert_hash}")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["name"] == "Public Holder"
        assert payload["cert_id"] == "PUBLIC-001"
        assert payload["course"] == "Public Course"
        assert token not in payload.values()
        assert "verification_token" not in payload

    def test_too_long_hash_in_report(self):
        # 128 char string (double SHA-256 length) — should be rejected
        r = self.client.get(f"/report/{'a' * 128}")
        assert r.status_code == 400

    def test_valid_format_nonexistent_hash_in_report(self):
        """Valid SHA-256 format but non-existent hash → 403 (no auth) or 404."""
        r = self.client.get(f"/report/{'a' * 64}")
        assert r.status_code in [403, 404]


class TestAdminAccess:
    """Verify admin-only endpoints require authentication."""

    def setup_method(self):
        self.client = app.test_client()
        # RBAC is always enforced; env var no longer gates admin routes
        os.environ["FLASK_ENV"] = "production"

    def teardown_method(self):
        os.environ["FLASK_ENV"] = "development"

    def test_ledger_no_auth_redirects_to_login(self):
        """Unauthenticated browser request to /ledger redirects to /login."""
        r = self.client.get("/ledger")
        assert r.status_code == 302
        assert "/login" in r.headers.get("Location", "")

    def test_ledger_with_query_param_still_redirects(self):
        """Admin key in URL query param must not work — headers only."""
        r = self.client.get("/ledger?admin_key=test-admin-key-12345")
        assert r.status_code == 302
        assert "/login" in r.headers.get("Location", "")

    def test_ledger_with_correct_legacy_header(self):
        """Legacy X-Admin-Key header still grants access (backward compat)."""
        r = self.client.get("/ledger", headers={"X-Admin-Key": "test-admin-key-12345"})
        # Auth layer passes; actual status depends on service state, not auth
        assert r.status_code != 302 and r.status_code != 401

    def test_api_export_unauthenticated_returns_401(self):
        """Unauthenticated request to an API-prefixed admin endpoint returns 401."""
        r = self.client.get("/api/export")
        assert r.status_code == 401

    def test_api_export_with_legacy_header_returns_403_not_401(self):
        """Authenticated but export-disabled request returns 403 (feature disabled)."""
        r = self.client.get("/api/export", headers={"X-Admin-Key": "test-admin-key-12345"})
        assert r.status_code == 403

    def test_legacy_admin_header_requires_feature_flag(self, monkeypatch):
        monkeypatch.setenv("ENABLE_LEGACY_ADMIN_KEY", "false")
        response = self.client.get(
            "/ledger",
            headers={"X-Admin-Key": "test-admin-key-12345"},
        )
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")

    def test_login_rejects_external_next_redirect(self, monkeypatch):
        monkeypatch.setitem(self.client.application.config, "WTF_CSRF_ENABLED", False)
        monkeypatch.setattr(limiter, "enabled", False)
        init_db()
        create_user("redirect_test", generate_password_hash("password"), "ADMIN")
        response = self.client.post(
            "/login?next=" + quote("https://attacker.example/phish", safe=""),
            data={"username": "redirect_test", "password": "password"},
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/")
        assert "attacker.example" not in response.headers["Location"]

    def test_login_allows_local_next_redirect(self, monkeypatch):
        monkeypatch.setitem(self.client.application.config, "WTF_CSRF_ENABLED", False)
        monkeypatch.setattr(limiter, "enabled", False)
        init_db()
        create_user("local_redirect_test", generate_password_hash("password"), "ADMIN")
        response = self.client.post(
            "/login?next=%2Fledger%3Fview%3Dfull",
            data={"username": "local_redirect_test", "password": "password"},
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/ledger?view=full")

    def test_logout_requires_post(self):
        response = self.client.get("/logout")
        assert response.status_code == 405

    def test_database_api_key_revocation_disables_authentication(self):
        init_db()
        create_user("key_revoke_test", generate_password_hash("password"), "ADMIN")
        user = get_user_by_username("key_revoke_test")
        raw_key = secrets.token_hex(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        create_api_key(user["id"], key_hash)
        assert get_user_by_api_key_hash(key_hash)["id"] == user["id"]
        assert revoke_api_key(key_hash)
        assert get_user_by_api_key_hash(key_hash) is None


class TestReportAccess:
    """Verify token-gated report download endpoint."""

    def setup_method(self):
        init_db()
        self.client = app.test_client()

    def test_no_token_returns_403(self):
        mock_hash = "a" * 64  # Valid SHA-256 format
        upsert_certificate(mock_hash, {"name": "Test", "certificate_title": "Test Cert"}, action="ISSUE")
        r = self.client.get(f"/report/{mock_hash}")
        assert r.status_code == 403

    def test_invalid_token_returns_403(self):
        mock_hash = "b" * 64
        upsert_certificate(mock_hash, {"name": "Test2", "certificate_title": "Test Cert 2"}, action="ISSUE")
        r = self.client.get(f"/report/{mock_hash}?token=not-a-real-token")
        assert r.status_code == 403

    def test_admin_key_correct_allows_access(self):
        mock_hash = "c" * 64
        upsert_certificate(mock_hash, {"name": "Test3", "certificate_title": "Test Cert 3"}, action="ISSUE")
        r = self.client.get(f"/report/{mock_hash}", headers={"X-Admin-Key": "test-admin-key-12345"})
        # Only test auth layer — PDF generation may fail without real data; accept 200 or report-gen error
        assert r.status_code in [200, 500]

    def test_correct_token_allows_access(self):
        mock_hash = "d" * 64
        token = upsert_certificate(mock_hash, {"name": "Test4", "certificate_title": "Test Cert 4"}, action="ISSUE")
        r = self.client.get(f"/report/{mock_hash}?token={token}")
        # Only test auth layer
        assert r.status_code in [200, 500]


class TestErrorHandlers:
    """Verify custom error handlers return correct status codes."""

    def setup_method(self):
        self.client = app.test_client()

    def test_404_returns_custom_page(self):
        r = self.client.get("/this-page-does-not-exist-ever")
        assert r.status_code == 404
        assert b"404" in r.data or b"Not Found" in r.data

    def test_api_404_returns_json(self):
        r = self.client.get("/api/this-does-not-exist")
        assert r.status_code == 404
        assert r.content_type.startswith("application/json")

    def test_invalid_hash_returns_400(self):
        r = self.client.get("/certificate/invalid")
        assert r.status_code == 400
        assert b"400" in r.data or b"Bad" in r.data


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
