"""Focused tests for cryptographic Google ID-token verification."""
import base64
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from backend.utils import google_oauth


CLIENT_ID = "certificateproject-test-client.apps.googleusercontent.com"
NONCE = "test-oauth-nonce"
KEY_ID = "test-google-key"


def _make_key_and_certificate():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test signing key")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    return private_key, certificate.public_bytes(serialization.Encoding.PEM)


TRUSTED_KEY, TRUSTED_CERT = _make_key_and_certificate()
UNTRUSTED_KEY, _ = _make_key_and_certificate()


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _signed_token(*, key=TRUSTED_KEY, audience=CLIENT_ID, expiry=None) -> str:
    now = int(time.time())
    header = {"alg": "RS256", "kid": KEY_ID, "typ": "JWT"}
    claims = {
        "iss": "https://accounts.google.com",
        "aud": audience,
        "sub": "google-user-123",
        "email": "recruiter@example.com",
        "email_verified": True,
        "nonce": NONCE,
        "iat": now,
        "exp": expiry if expiry is not None else now + 300,
    }
    signing_input = (
        f"{_b64url(json.dumps(header).encode())}."
        f"{_b64url(json.dumps(claims).encode())}"
    )
    signature = key.sign(
        signing_input.encode("ascii"), padding.PKCS1v15(), hashes.SHA256()
    )
    return f"{signing_input}.{_b64url(signature)}"


class _MockTokenResponse:
    def __init__(self, token):
        self.data = json.dumps({"id_token": token}).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.data


class _MockGoogleKeyRequest:
    """Serve a mocked Google signing certificate without network access."""

    def __call__(self, _url, method="GET", **_kwargs):
        assert method == "GET"
        response_data = json.dumps({KEY_ID: TRUSTED_CERT.decode("ascii")}).encode()
        return type(
            "Response", (), {"status": 200, "headers": {}, "data": response_data}
        )()


@pytest.fixture(autouse=True)
def mock_google_requests(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(google_oauth, "GoogleAuthRequest", _MockGoogleKeyRequest)
    monkeypatch.setattr(
        google_oauth,
        "urlopen",
        lambda *_args, **_kwargs: _MockTokenResponse(_signed_token()),
    )


def _flow():
    return {
        "state": "state-is-validated-by-the-flask-callback",
        "nonce": NONCE,
        "verifier": "pkce-verifier-preserved-for-the-token-exchange",
        "ts": int(time.time()),
    }


def _exchange():
    return google_oauth.exchange_code_for_claims(
        "authorization-code",
        "https://app.example/auth/google/callback",
        _flow(),
    )


def test_valid_google_id_token_is_verified_and_claims_are_returned():
    claims = _exchange()

    assert claims["sub"] == "google-user-123"
    assert claims["email"] == "recruiter@example.com"
    assert claims["aud"] == CLIENT_ID


def test_invalid_signature_is_rejected(monkeypatch):
    token = _signed_token(key=UNTRUSTED_KEY)
    monkeypatch.setattr(
        google_oauth, "urlopen", lambda *_args, **_kwargs: _MockTokenResponse(token)
    )

    with pytest.raises(google_oauth.GoogleOAuthError, match="ID token verification failed"):
        _exchange()


def test_wrong_audience_is_rejected(monkeypatch):
    token = _signed_token(audience="another-client.apps.googleusercontent.com")
    monkeypatch.setattr(
        google_oauth, "urlopen", lambda *_args, **_kwargs: _MockTokenResponse(token)
    )

    with pytest.raises(google_oauth.GoogleOAuthError, match="ID token verification failed"):
        _exchange()


def test_expired_token_is_rejected(monkeypatch):
    token = _signed_token(expiry=int(time.time()) - 60)
    monkeypatch.setattr(
        google_oauth, "urlopen", lambda *_args, **_kwargs: _MockTokenResponse(token)
    )

    with pytest.raises(google_oauth.GoogleOAuthError, match="ID token verification failed"):
        _exchange()
