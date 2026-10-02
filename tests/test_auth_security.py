"""
test_auth_security.py — focused security tests for the new authentication
features (email verification, TOTP second factor + recovery codes, password
reset, redirect handling and the SQLite guarantees behind them).

Each test uses its own client/source address because the authentication
endpoints are rate limited by client address; sharing one address would make
tests interfere with each other.
"""
import hashlib
import itertools
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pyotp
from flask import session as flask_session
from flask_wtf.csrf import generate_csrf
from werkzeug.security import generate_password_hash

import app as app_module
import backend.database.db as db_module
from app import app
from backend.database.db import (
    consume_auth_token,
    create_auth_token,
    create_user,
    get_user_by_email,
    get_user_by_username,
    init_db,
)

PAST = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
FUTURE = "2999-01-01T00:00:00+00:00"
PASSWORD = "correct horse battery"
NEW_PASSWORD = "a much better password"
AUTH_ORIGIN = "https://certauth.example"
_ADDRESS_COUNTER = itertools.count(1)


def _unique(prefix):
    return f"{prefix}-{uuid.uuid4().hex}"


def _new_client():
    """Client with a unique source address so rate limits stay per-test.

    Addresses are handed out from the benchmarking range (198.18.0.0/15) and
    never repeat inside a process, so no two tests can share a rate-limit
    bucket. (The other authentication tests use 203.0.113.x, which is a
    different range, so the two files cannot collide either.)
    """
    client = app.test_client()
    unique = next(_ADDRESS_COUNTER)
    client.environ_base["REMOTE_ADDR"] = f"198.18.{unique // 250}.{unique % 250 + 1}"
    return client


def _csrf_headers(client):
    """Sign a CSRF token into the client session and return the header for it."""
    with app.test_request_context():
        token = generate_csrf()
        raw = flask_session["csrf_token"]
    with client.session_transaction() as client_session:
        client_session["csrf_token"] = raw
    return {"X-CSRFToken": token}


def _token_from_email(body):
    match = re.search(r"/(verify-email|reset-password)/([A-Za-z0-9_\-]+)", body)
    assert match, f"no token found in email body: {body!r}"
    return match.group(2)


def _make_user(email=None, password=PASSWORD, verified=False):
    """Create a user directly in the database; returns (username, user_id)."""
    username = _unique("sec")
    assert create_user(username, generate_password_hash(password), "VERIFIER", email)
    user = get_user_by_username(username)
    if verified and email:
        db_module.update_user_email_verified(user["id"])
    return username, user["id"]


def _login(client, username, password=PASSWORD, query=""):
    return client.post(
        f"/login{query}",
        data={"username": username, "password": password},
        headers=_csrf_headers(client),
    )


def _enable_two_factor(client):
    """Complete the TOTP enrolment flow for the currently logged-in client."""
    setup = client.post("/2fa/setup", data={"password": PASSWORD}, headers=_csrf_headers(client))
    assert setup.status_code == 200, setup.data
    payload = setup.get_json()
    enabled = client.post(
        "/2fa/enable",
        data={"code": pyotp.TOTP(payload["secret"]).now()},
        headers=_csrf_headers(client),
    )
    assert enabled.status_code == 200, enabled.data
    return payload


def _rows(query, params=()):
    with sqlite3.connect(db_module._DB_PATH) as conn:
        return conn.execute(query, params).fetchall()



class TestEmailVerification:
    """Verification links must be random, hashed, single-use and expiring."""

    def test_valid_token_verifies_account_and_is_stored_only_as_a_hash(self, monkeypatch):
        init_db()
        monkeypatch.setitem(app.config, "AUTH_BASE_URL", AUTH_ORIGIN)
        sent = []
        monkeypatch.setattr(app_module, "_send_auth_email", lambda *args: sent.append(args) or True)
        client = _new_client()
        email = f"{_unique('ver')}@example.test"

        response = client.post(
            "/register",
            data={"username": _unique("ver"), "email": email, "password": PASSWORD},
            headers=_csrf_headers(client),
        )
        assert response.status_code == 202
        raw_token = _token_from_email(sent.pop()[2])

        stored_hashes = {
            row[0]
            for row in _rows("SELECT token_hash FROM auth_tokens WHERE purpose = ?", ("email_verification",))
        }
        assert hashlib.sha256(raw_token.encode()).hexdigest() in stored_hashes
        assert raw_token not in stored_hashes

        assert client.get(f"/verify-email/{raw_token}").status_code == 200
        assert get_user_by_email(email)["email_verified"] == 1

    def test_expired_token_is_rejected(self):
        init_db()
        _, user_id = _make_user(email=f"{_unique('exp')}@example.test")
        raw_token = f"expired-{uuid.uuid4().hex}"
        create_auth_token(user_id, "email_verification", raw_token, PAST)

        assert _new_client().get(f"/verify-email/{raw_token}").status_code == 400
        assert consume_auth_token(raw_token, "email_verification") is None

    def test_token_cannot_be_reused(self):
        init_db()
        _, user_id = _make_user(email=f"{_unique('reuse')}@example.test")
        raw_token = f"single-{uuid.uuid4().hex}"
        create_auth_token(user_id, "email_verification", raw_token, FUTURE)
        client = _new_client()

        assert client.get(f"/verify-email/{raw_token}").status_code == 200
        assert client.get(f"/verify-email/{raw_token}").status_code == 400
        assert consume_auth_token(raw_token, "email_verification") is None

    def test_resend_is_rate_limited(self):
        init_db()
        client = _new_client()
        headers = _csrf_headers(client)
        email = f"{_unique('resend')}@example.test"

        statuses = [
            client.post("/resend-verification", data={"email": email}, headers=headers).status_code
            for _ in range(4)
        ]
        assert statuses[:3] == [202, 202, 202]
        assert statuses[3] == 429

    def test_resend_does_not_reveal_whether_an_account_exists(self):
        init_db()
        client = _new_client()
        known_email = f"{_unique('known')}@example.test"
        _make_user(email=known_email)

        unknown = client.post(
            "/resend-verification",
            data={"email": f"{_unique('missing')}@example.test"},
            headers=_csrf_headers(client),
        )
        known = client.post(
            "/resend-verification", data={"email": known_email}, headers=_csrf_headers(client)
        )
        assert unknown.status_code == known.status_code == 202
        assert unknown.get_json() == known.get_json()

    def test_registration_does_not_reveal_existing_accounts(self, monkeypatch):
        init_db()
        monkeypatch.setitem(app.config, "AUTH_BASE_URL", AUTH_ORIGIN)
        monkeypatch.setattr(app_module, "_send_auth_email", lambda *args: True)
        client = _new_client()
        data = {
            "username": _unique("dup"),
            "email": f"{_unique('dup')}@example.test",
            "password": PASSWORD,
        }

        first = client.post("/register", data=data, headers=_csrf_headers(client))
        second = client.post("/register", data=data, headers=_csrf_headers(client))
        assert first.status_code == second.status_code == 202
        assert first.get_json() == second.get_json()


class TestTwoFactorAuthentication:
    def test_setup_and_enable_require_authentication(self):
        init_db()
        client = _new_client()

        assert client.post(
            "/2fa/setup", data={"password": PASSWORD}, headers=_csrf_headers(client)
        ).status_code == 401
        assert client.post(
            "/2fa/enable", data={"code": "123456"}, headers=_csrf_headers(client)
        ).status_code == 400
        with client.session_transaction() as current:
            assert "user_id" not in current

    def test_enabling_requires_a_code_from_the_new_secret(self):
        init_db()
        username, _ = _make_user()
        client = _new_client()
        assert _login(client, username).status_code == 302

        setup = client.post("/2fa/setup", data={"password": PASSWORD}, headers=_csrf_headers(client))
        assert setup.status_code == 200
        secret = setup.get_json()["secret"]

        assert client.post(
            "/2fa/enable", data={"code": "000000"}, headers=_csrf_headers(client)
        ).status_code == 400
        assert get_user_by_username(username)["totp_enabled"] == 0

        assert client.post(
            "/2fa/enable",
            data={"code": pyotp.TOTP(secret).now()},
            headers=_csrf_headers(client),
        ).status_code == 200
        user = get_user_by_username(username)
        assert user["totp_enabled"] == 1
        assert user["totp_secret"] == secret

    def test_recovery_codes_are_stored_as_hashes_only(self):
        init_db()
        username, _ = _make_user()
        client = _new_client()
        assert _login(client, username).status_code == 302

        payload = _enable_two_factor(client)
        stored = get_user_by_username(username)["recovery_codes"]
        assert len(payload["recovery_codes"]) == 8
        for code in payload["recovery_codes"]:
            assert code not in stored
            assert hashlib.sha256(code.encode()).hexdigest() in stored


    def test_login_with_2fa_requires_the_second_factor(self):
        init_db()
        username, user_id = _make_user()
        enroller = _new_client()
        assert _login(enroller, username).status_code == 302
        _enable_two_factor(enroller)

        client = _new_client()
        response = _login(client, username)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/2fa/verify")
        with client.session_transaction() as pending:
            assert "user_id" not in pending
            assert pending["pending_2fa_user_id"] == user_id
        # the half-authenticated state cannot be used as an authenticated session
        assert client.post(
            "/2fa/setup", data={"password": PASSWORD}, headers=_csrf_headers(client)
        ).status_code == 401

    def test_invalid_code_is_rejected_and_valid_code_completes_login(self):
        init_db()
        username, user_id = _make_user()
        enroller = _new_client()
        assert _login(enroller, username).status_code == 302
        secret = _enable_two_factor(enroller)["secret"]

        client = _new_client()
        assert _login(client, username).status_code == 302
        assert client.post(
            "/2fa/verify", data={"code": "000000"}, headers=_csrf_headers(client)
        ).status_code == 401
        with client.session_transaction() as pending:
            assert "user_id" not in pending

        response = client.post(
            "/2fa/verify",
            data={"code": pyotp.TOTP(secret).now()},
            headers=_csrf_headers(client),
        )
        assert response.status_code == 302
        with client.session_transaction() as authenticated:
            assert authenticated["user_id"] == user_id
        # the promoted session really is fully authenticated: it can re-enter
        # enrolment (password + current code, as required once 2FA is on)
        assert client.post(
            "/2fa/setup", data={"password": PASSWORD}, headers=_csrf_headers(client)
        ).status_code == 401
        assert client.post(
            "/2fa/setup",
            data={"password": PASSWORD, "current_code": pyotp.TOTP(secret).now()},
            headers=_csrf_headers(client),
        ).status_code == 200

    def test_totp_guessing_is_rate_limited(self):
        init_db()
        username, _ = _make_user()
        enroller = _new_client()
        assert _login(enroller, username).status_code == 302
        _enable_two_factor(enroller)

        attacker = _new_client()
        assert _login(attacker, username).status_code == 302
        headers = _csrf_headers(attacker)
        statuses = [
            attacker.post("/2fa/verify", data={"code": "000000"}, headers=headers).status_code
            for _ in range(6)
        ]
        assert 429 in statuses
        assert 302 not in statuses
        with attacker.session_transaction() as pending:
            assert "user_id" not in pending

    def test_second_factor_throttle_cannot_be_bypassed_by_rotating_addresses(self):
        init_db()
        username, _ = _make_user()
        enroller = _new_client()
        assert _login(enroller, username).status_code == 302
        _enable_two_factor(enroller)

        attacker = _new_client()
        assert _login(attacker, username).status_code == 302
        headers = _csrf_headers(attacker)
        session_cookie = attacker.get_cookie(app.config["SESSION_COOKIE_NAME"])

        statuses = []
        for _ in range(6):
            # every attempt comes from a brand new source address, so only the
            # per-account bucket can produce a 429 here
            rotated = _new_client()
            rotated.set_cookie(app.config["SESSION_COOKIE_NAME"], session_cookie.value)
            statuses.append(
                rotated.post("/2fa/verify", data={"code": "000000"}, headers=headers).status_code
            )
        assert 429 in statuses
        assert 302 not in statuses

    def test_recovery_code_works_exactly_once(self):
        init_db()
        username, user_id = _make_user()
        enroller = _new_client()
        assert _login(enroller, username).status_code == 302
        recovery_code = _enable_two_factor(enroller)["recovery_codes"][0]

        first = _new_client()
        assert _login(first, username).status_code == 302
        assert first.post(
            "/2fa/verify", data={"code": recovery_code}, headers=_csrf_headers(first)
        ).status_code == 302
        with first.session_transaction() as authenticated:
            assert authenticated["user_id"] == user_id

        second = _new_client()
        assert _login(second, username).status_code == 302
        assert second.post(
            "/2fa/verify", data={"code": recovery_code}, headers=_csrf_headers(second)
        ).status_code == 401
        with second.session_transaction() as pending:
            assert "user_id" not in pending

    def test_pending_second_factor_state_expires(self):
        init_db()
        username, _ = _make_user()
        enroller = _new_client()
        assert _login(enroller, username).status_code == 302
        _enable_two_factor(enroller)

        stale = _new_client()
        assert _login(stale, username).status_code == 302
        with stale.session_transaction() as pending:
            pending["pending_2fa_started_at"] = (
                datetime.now(timezone.utc) - timedelta(minutes=30)
            ).isoformat()

        assert stale.post(
            "/2fa/verify", data={"code": "000000"}, headers=_csrf_headers(stale)
        ).status_code == 401
        with stale.session_transaction() as current:
            assert "pending_2fa_user_id" not in current
            assert "user_id" not in current


class TestPasswordReset:
    def test_valid_reset_token_changes_the_password_once(self, monkeypatch):
        init_db()
        monkeypatch.setitem(app.config, "AUTH_BASE_URL", AUTH_ORIGIN)
        sent = []
        monkeypatch.setattr(app_module, "_send_auth_email", lambda *args: sent.append(args) or True)
        email = f"{_unique('reset')}@example.test"
        username, _ = _make_user(email=email, verified=True)
        client = _new_client()

        assert client.post(
            "/forgot-password", data={"email": email}, headers=_csrf_headers(client)
        ).status_code == 202
        raw_token = _token_from_email(sent.pop()[2])

        assert client.post(
            f"/reset-password/{raw_token}",
            data={"password": NEW_PASSWORD},
            headers=_csrf_headers(client),
        ).status_code == 200
        assert _login(_new_client(), username, NEW_PASSWORD).status_code == 302
        assert _login(_new_client(), username, PASSWORD).status_code == 401

    def test_expired_reset_token_is_rejected(self):
        init_db()
        _, user_id = _make_user(email=f"{_unique('exppw')}@example.test", verified=True)
        raw_token = f"expired-{uuid.uuid4().hex}"
        create_auth_token(user_id, "password_reset", raw_token, PAST)

        client = _new_client()
        assert client.post(
            f"/reset-password/{raw_token}",
            data={"password": NEW_PASSWORD},
            headers=_csrf_headers(client),
        ).status_code == 400
        assert consume_auth_token(raw_token, "password_reset") is None

    def test_reset_token_cannot_be_reused(self):
        init_db()
        _, user_id = _make_user(email=f"{_unique('reuse')}@example.test", verified=True)
        raw_token = f"once-{uuid.uuid4().hex}"
        create_auth_token(user_id, "password_reset", raw_token, FUTURE)

        client = _new_client()
        assert client.post(
            f"/reset-password/{raw_token}",
            data={"password": NEW_PASSWORD},
            headers=_csrf_headers(client),
        ).status_code == 200
        assert client.post(
            f"/reset-password/{raw_token}",
            data={"password": "yet another password"},
            headers=_csrf_headers(client),
        ).status_code == 400

    def test_weak_password_does_not_burn_the_reset_token(self):
        init_db()
        _, user_id = _make_user(email=f"{_unique('weak')}@example.test", verified=True)
        raw_token = f"weak-{uuid.uuid4().hex}"
        create_auth_token(user_id, "password_reset", raw_token, FUTURE)

        client = _new_client()
        assert client.post(
            f"/reset-password/{raw_token}",
            data={"password": "short"},
            headers=_csrf_headers(client),
        ).status_code == 400
        assert client.post(
            f"/reset-password/{raw_token}",
            data={"password": NEW_PASSWORD},
            headers=_csrf_headers(client),
        ).status_code == 200

    def test_reset_link_page_does_not_consume_the_token(self):
        init_db()
        _, user_id = _make_user(email=f"{_unique('page')}@example.test", verified=True)
        raw_token = f"page-{uuid.uuid4().hex}"
        create_auth_token(user_id, "password_reset", raw_token, FUTURE)

        client = _new_client()
        assert client.get(f"/reset-password/{raw_token}").status_code == 200
        assert client.post(
            f"/reset-password/{raw_token}",
            data={"password": NEW_PASSWORD},
            headers=_csrf_headers(client),
        ).status_code == 200

    def test_forgot_password_is_rate_limited(self):
        init_db()
        client = _new_client()
        headers = _csrf_headers(client)
        email = f"{_unique('limit')}@example.test"

        statuses = [
            client.post("/forgot-password", data={"email": email}, headers=headers).status_code
            for _ in range(4)
        ]
        assert statuses[:3] == [202, 202, 202]
        assert statuses[3] == 429

    def test_reset_password_is_rate_limited(self):
        init_db()
        client = _new_client()
        headers = _csrf_headers(client)
        token = f"invalid-{uuid.uuid4().hex}"

        statuses = [
            client.post(
                f"/reset-password/{token}",
                data={"password": NEW_PASSWORD},
                headers=headers,
            ).status_code
            for _ in range(6)
        ]

        assert statuses[:5] == [400] * 5
        assert statuses[5] == 429

    def test_reset_invalidates_existing_sessions(self):
        init_db()
        username, user_id = _make_user()
        existing = _new_client()
        assert _login(existing, username).status_code == 302
        with existing.session_transaction() as authenticated:
            assert authenticated["user_id"] == user_id

        raw_token = f"invalidate-{uuid.uuid4().hex}"
        create_auth_token(user_id, "password_reset", raw_token, FUTURE)
        resetter = _new_client()
        assert resetter.post(
            f"/reset-password/{raw_token}",
            data={"password": NEW_PASSWORD},
            headers=_csrf_headers(resetter),
        ).status_code == 200

        assert existing.post(
            "/2fa/setup", data={"password": NEW_PASSWORD}, headers=_csrf_headers(existing)
        ).status_code == 401
        with existing.session_transaction() as stale:
            assert "user_id" not in stale


class TestRedirectSecurity:
    def test_external_next_targets_are_ignored(self):
        init_db()
        username, user_id = _make_user()

        for hostile in (
            "https://evil.example/phish",
            "http://evil.example",
            "//evil.example/phish",
            "/\\evil.example",
        ):
            client = _new_client()
            response = _login(client, username, query=f"?next={quote(hostile, safe='')}")
            assert response.status_code == 302
            location = response.headers["Location"]
            assert "evil.example" not in location, (hostile, location)
            with client.session_transaction() as authenticated:
                assert authenticated["user_id"] == user_id

    def test_same_origin_next_targets_are_honoured(self):
        init_db()
        username, _ = _make_user()

        relative = _login(_new_client(), username, query="?next=%2Fissue")
        assert relative.status_code == 302
        assert relative.headers["Location"].endswith("/issue")

        absolute = _login(
            _new_client(), username, query=f"?next={quote('http://localhost/issue', safe='')}"
        )
        assert absolute.status_code == 302
        assert absolute.headers["Location"].endswith("/issue")

    def test_second_factor_step_keeps_only_safe_next_targets(self):
        init_db()
        username, _ = _make_user()
        enroller = _new_client()
        assert _login(enroller, username).status_code == 302
        secret = _enable_two_factor(enroller)["secret"]

        hostile = _new_client()
        assert _login(
            hostile, username, query=f"?next={quote('https://evil.example/phish', safe='')}"
        ).status_code == 302
        hostile_response = hostile.post(
            "/2fa/verify",
            data={"code": pyotp.TOTP(secret).now()},
            headers=_csrf_headers(hostile),
        )
        assert hostile_response.status_code == 302
        assert "evil.example" not in hostile_response.headers["Location"]

        friendly = _new_client()
        assert _login(friendly, username, query="?next=%2Fissue").status_code == 302
        friendly_response = friendly.post(
            "/2fa/verify",
            data={"code": pyotp.TOTP(secret).now()},
            headers=_csrf_headers(friendly),
        )
        assert friendly_response.status_code == 302
        assert friendly_response.headers["Location"].endswith("/issue")


class TestMailAndMigrationRobustness:
    def test_email_delivery_failure_does_not_500_or_log_the_token(self, monkeypatch, caplog):
        init_db()
        monkeypatch.setitem(app.config, "AUTH_BASE_URL", AUTH_ORIGIN)
        bodies = []

        def _explode(address, subject, body):
            bodies.append(body)
            raise OSError("smtp transport is down")

        monkeypatch.setattr(app_module, "_send_auth_email", _explode)
        email = f"{_unique('smtp')}@example.test"
        client = _new_client()
        with caplog.at_level("DEBUG"):
            response = client.post(
                "/register",
                data={"username": _unique("smtp"), "email": email, "password": PASSWORD},
                headers=_csrf_headers(client),
            )

        assert response.status_code == 202
        assert get_user_by_email(email) is not None
        token = _token_from_email(bodies[0])
        assert token not in caplog.text

    def test_smtp_transport_error_inside_send_auth_email_is_contained(self, monkeypatch):
        init_db()
        monkeypatch.setitem(app.config, "AUTH_BASE_URL", AUTH_ORIGIN)
        monkeypatch.setenv("SMTP_HOST", "smtp.example")
        monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
        monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-secret")

        def _refuse(*args, **kwargs):
            raise OSError("connection refused")

        monkeypatch.setattr(app_module.smtplib, "SMTP", _refuse)
        email = f"{_unique('refuse')}@example.test"
        client = _new_client()
        response = client.post(
            "/register",
            data={"username": _unique("refuse"), "email": email, "password": PASSWORD},
            headers=_csrf_headers(client),
        )
        assert response.status_code == 202
        assert get_user_by_email(email) is not None

    def test_non_https_auth_base_url_does_not_500(self, monkeypatch):
        init_db()
        monkeypatch.setitem(app.config, "AUTH_BASE_URL", "http://insecure.example")

        def _must_not_send(*args, **kwargs):
            raise AssertionError("no email should be sent for a non-HTTPS origin")

        monkeypatch.setattr(app_module, "_send_auth_email", _must_not_send)
        client = _new_client()
        response = client.post(
            "/register",
            data={
                "username": _unique("origin"),
                "email": f"{_unique('origin')}@example.test",
                "password": PASSWORD,
            },
            headers=_csrf_headers(client),
        )
        assert response.status_code == 202

    def test_migration_keeps_existing_accounts_able_to_sign_in(self, tmp_path, monkeypatch):
        legacy = tmp_path / "legacy.db"
        with sqlite3.connect(legacy) as conn:
            conn.execute(
                """CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'VERIFIER',
                    created_at TEXT NOT NULL
                )"""
            )
            conn.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                ("legacy-user", "legacy@example.test", "unused-hash", "2026-01-01T00:00:00+00:00"),
            )
            conn.commit()
        monkeypatch.setattr(db_module, "_DB_PATH", str(legacy))

        db_module.init_db()
        assert db_module.get_user_by_username("legacy-user")["email_verified"] == 1
        # accounts created after the migration still have to verify
        assert db_module.create_user("fresh-user", "hash", "VERIFIER", "fresh@example.test")
        assert db_module.get_user_by_username("fresh-user")["email_verified"] == 0


class TestAtomicConsumption:
    """Consumption must be exact under concurrent requests.

    These tests run against an isolated database file: the point is to exercise
    concurrent writers, and sharing the repository database with other test
    processes would only add unrelated lock contention.
    """

    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db_module, "_DB_PATH", str(tmp_path / "atomic.db"))
        db_module.init_db()

    def _consume_concurrently(self, consume, attempts=4):
        results = []
        barrier = threading.Barrier(attempts)

        def worker():
            barrier.wait()
            results.append(consume())

        threads = [threading.Thread(target=worker) for _ in range(attempts)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    def test_auth_token_is_consumed_by_exactly_one_request(self, tmp_path, monkeypatch):
        self._isolated_db(tmp_path, monkeypatch)
        _, user_id = _make_user(email=f"{_unique('atomic')}@example.test")
        raw_token = f"atomic-{uuid.uuid4().hex}"
        create_auth_token(user_id, "password_reset", raw_token, FUTURE)

        results = self._consume_concurrently(
            lambda: consume_auth_token(raw_token, "password_reset")
        )
        assert results.count(user_id) == 1

    def test_recovery_code_is_consumed_by_exactly_one_request(self, tmp_path, monkeypatch):
        self._isolated_db(tmp_path, monkeypatch)
        recovery_codes = [uuid.uuid4().hex for _ in range(8)]
        _, user_id = _make_user()
        db_module.update_user_totp(
            user_id,
            pyotp.random_base32(),
            [hashlib.sha256(code.encode()).hexdigest() for code in recovery_codes],
        )
        code_hash = hashlib.sha256(recovery_codes[0].encode()).hexdigest()

        results = self._consume_concurrently(
            lambda: db_module.consume_recovery_code(user_id, code_hash)
        )
        assert results.count(True) == 1
