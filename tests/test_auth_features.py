import re
import uuid
from unittest.mock import Mock

import pyotp
from werkzeug.security import generate_password_hash
from flask import session
from flask_wtf.csrf import generate_csrf

from app import app, _send_auth_email
from backend.database.db import (
    consume_auth_token,
    create_auth_token,
    create_user,
    get_user_by_username,
    init_db,
)


def _token_from(message):
    return re.search(r"/(verify-email|reset-password)/([A-Za-z0-9_-]+)", message).group(2)


def _new_client():
    client = app.test_client()
    client.environ_base["REMOTE_ADDR"] = f"198.51.100.{uuid.uuid4().int % 250 + 1}"
    return client


def _csrf_headers(client, cookie_domain=None):
    with app.test_request_context():
        token = generate_csrf()
        session_value = session["csrf_token"]
    with client.session_transaction() as client_session:
        client_session["csrf_token"] = session_value
    if cookie_domain:
        cookie = client.get_cookie(app.config["SESSION_COOKIE_NAME"])
        client.set_cookie(app.config["SESSION_COOKIE_NAME"], cookie.value, domain=cookie_domain)
    return {"X-CSRFToken": token}


def test_email_verification_and_password_reset_are_single_use(monkeypatch):
    init_db()
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", True)
    monkeypatch.setitem(app.config, "AUTH_BASE_URL", "https://certauth.example")
    sent = []
    monkeypatch.setattr("app._send_auth_email", lambda *args: sent.append(args) or True)
    client = _new_client()
    username = "auth-" + uuid.uuid4().hex
    email = username + "@example.test"

    assert client.post(
        "/register",
        data={"username": username, "email": email, "password": "correct horse battery"},
        headers={"Host": "attacker.example"},
    ).status_code == 400
    csrf_headers = _csrf_headers(client, "attacker.example")
    response = client.post(
        "/register",
        base_url="http://attacker.example",
        data={"username": username, "email": email, "password": "correct horse battery"},
        headers=csrf_headers,
    )
    assert response.status_code == 202
    verify_message = sent.pop()[2]
    assert verify_message.startswith("https://certauth.example/")
    verify_token = _token_from(verify_message)
    assert client.post(
        "/resend-verification",
        base_url="http://attacker.example",
        data={"email": email},
        headers=_csrf_headers(client, "attacker.example"),
    ).status_code == 202
    resend_message = sent.pop()[2]
    assert resend_message.startswith("https://certauth.example/")
    verify_token = _token_from(resend_message)
    assert client.get("/verify-email/" + verify_token).status_code == 200

    client.post(
        "/forgot-password",
        base_url="http://attacker.example",
        data={"email": email},
        headers=_csrf_headers(client, "attacker.example"),
    )
    reset_message = sent.pop()[2]
    assert reset_message.startswith("https://certauth.example/")
    reset_token = _token_from(reset_message)
    assert client.post(
        "/reset-password/" + reset_token,
        data={"password": "new secure password"},
        headers=_csrf_headers(client, "attacker.example"),
    ).status_code == 200
    assert client.post(
        "/reset-password/" + reset_token,
        data={"password": "another password"},
        headers=_csrf_headers(client),
    ).status_code == 400


def test_totp_setup_requires_password_reauthentication_and_recovery_is_single_use(monkeypatch):
    init_db()
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", True)
    username = "totp-" + uuid.uuid4().hex
    assert create_user(username, generate_password_hash("password one"), "VERIFIER")
    client = _new_client()
    assert client.post(
        "/login", data={"username": username, "password": "password one"},
        headers=_csrf_headers(client),
    ).status_code == 302
    assert client.post("/2fa/setup", headers=_csrf_headers(client)).status_code == 401
    setup = client.post(
        "/2fa/setup",
        data={"password": "password one"},
        headers=_csrf_headers(client),
    )
    assert setup.status_code == 200
    payload = setup.get_json()
    assert len(payload["recovery_codes"]) == 8
    assert all(len(code) == 32 for code in payload["recovery_codes"])
    assert client.post(
        "/2fa/enable",
        data={"code": pyotp.TOTP(payload["secret"]).now()},
        headers=_csrf_headers(client),
    ).status_code == 200
    with client.session_transaction() as session:
        session.clear()
    assert client.post(
        "/login", data={"username": username, "password": "password one"},
        headers=_csrf_headers(client),
    ).status_code == 302
    assert client.post("/2fa/verify", data={"code": pyotp.TOTP(payload["secret"]).now()},
                       headers=_csrf_headers(client)).status_code == 302
    with client.session_transaction() as authenticated:
        assert authenticated["user_id"] == get_user_by_username(username)["id"]

    assert client.post(
        "/2fa/setup",
        data={"password": "password one"},
        headers=_csrf_headers(client),
    ).status_code == 401
    changed_factor = client.post(
        "/2fa/setup",
        data={
            "password": "password one",
            "current_code": pyotp.TOTP(payload["secret"]).now(),
        },
        headers=_csrf_headers(client),
    )
    assert changed_factor.status_code == 200
    assert changed_factor.get_json()["secret"] != payload["secret"]

    with client.session_transaction() as current:
        current.clear()
    assert client.post(
        "/login", data={"username": username, "password": "password one"},
        headers=_csrf_headers(client),
    ).status_code == 302
    code = payload["recovery_codes"][0]
    assert client.post("/2fa/verify", data={"code": code}, headers=_csrf_headers(client)).status_code == 302
    with client.session_transaction() as current:
        current.clear()
    client.post("/login", data={"username": username, "password": "password one"},
                headers=_csrf_headers(client))
    assert client.post("/2fa/verify", data={"code": code}, headers=_csrf_headers(client)).status_code == 401


def test_new_auth_token_invalidates_older_token():
    init_db()
    username = "rotation-" + uuid.uuid4().hex
    assert create_user(username, generate_password_hash("password one"), "VERIFIER")
    user_id = get_user_by_username(username)["id"]
    old_token = "old-" + uuid.uuid4().hex
    new_token = "new-" + uuid.uuid4().hex
    create_auth_token(user_id, "password_reset", old_token, "2999-01-01T00:00:00+00:00")
    create_auth_token(user_id, "password_reset", new_token, "2999-01-01T00:00:00+00:00")
    assert consume_auth_token(old_token, "password_reset") is None
    assert consume_auth_token(new_token, "password_reset") == user_id


def test_recovery_codes_have_at_least_128_bits_of_randomness(monkeypatch):
    init_db()
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", True)
    username = "entropy-" + uuid.uuid4().hex
    assert create_user(username, generate_password_hash("password one"), "VERIFIER")
    client = _new_client()
    assert client.post("/login", data={"username": username, "password": "password one"},
                       headers=_csrf_headers(client)).status_code == 302
    response = client.post("/2fa/setup", data={"password": "password one"},
                           headers=_csrf_headers(client))
    codes = response.get_json()["recovery_codes"]
    assert len(codes) == 8
    assert all(len(code) == 32 for code in codes)
    assert all(set(code) <= set("0123456789abcdef") for code in codes)


def test_smtp_starttls_uses_certificate_validating_context(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.test")
    monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("SMTP_PASSWORD", "not-a-real-secret")
    context = object()
    starttls = Mock()
    smtp_client = Mock()
    smtp_client.__enter__ = Mock(return_value=smtp_client)
    smtp_client.__exit__ = Mock(return_value=False)
    smtp_client.starttls = starttls
    monkeypatch.setattr("app.ssl.create_default_context", lambda: context)
    monkeypatch.setattr("app.smtplib.SMTP", lambda *args, **kwargs: smtp_client)

    assert _send_auth_email("recipient@example.test", "Test", "Body")
    starttls.assert_called_once_with(context=context)


def test_password_reset_invalidates_other_authenticated_sessions(monkeypatch):
    init_db()
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", True)
    username = "session-" + uuid.uuid4().hex
    assert create_user(username, generate_password_hash("password one"), "VERIFIER")
    user_id = get_user_by_username(username)["id"]

    existing_client = _new_client()
    assert existing_client.post(
        "/login", data={"username": username, "password": "password one"},
        headers=_csrf_headers(existing_client),
    ).status_code == 302
    with existing_client.session_transaction() as authenticated:
        assert authenticated["auth_version"] == get_user_by_username(username)["auth_version"]

    reset_token = "reset-" + uuid.uuid4().hex
    create_auth_token(user_id, "password_reset", reset_token, "2999-01-01T00:00:00+00:00")
    reset_client = _new_client()
    response = reset_client.post(
        "/reset-password/" + reset_token,
        data={"password": "new password value"},
        headers=_csrf_headers(reset_client),
    )
    assert response.status_code == 200

    stale_session_response = existing_client.post(
        "/2fa/setup",
        data={"password": "new password value"},
        headers=_csrf_headers(existing_client),
    )
    assert stale_session_response.status_code == 401
    with existing_client.session_transaction() as stale_session:
        assert "user_id" not in stale_session
