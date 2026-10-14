"""Google OAuth 2.0 / OpenID Connect helper (authorization-code + PKCE).

Configuration (environment variables, never hard-coded):
    GOOGLE_CLIENT_ID                 OAuth client ID from Google Cloud Console
    GOOGLE_CLIENT_SECRET             OAuth client secret from Google Cloud Console
    GOOGLE_REDIRECT_URI              (optional) exact callback URL registered in Google
    GOOGLE_ALLOWED_EMAIL_DOMAINS     (optional) comma-separated allow-list, e.g. "acme.com,corp.io"

If GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are missing the feature is simply
disabled and the sign-in button is not rendered.
"""
import base64
import hashlib
import json
import os
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
VALID_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
FLOW_MAX_AGE_SECONDS = 600
_PLACEHOLDER_MARKERS = ("your_", "change_me", "changeme", "placeholder", "example")


class GoogleOAuthError(Exception):
    """Raised when the Google sign-in handshake cannot be completed safely."""


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def is_configured() -> bool:
    client_id, client_secret = _env("GOOGLE_CLIENT_ID"), _env("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return False
    combined = (client_id + client_secret).casefold()
    return not any(marker in combined for marker in _PLACEHOLDER_MARKERS)


def allowed_domains() -> set:
    raw = _env("GOOGLE_ALLOWED_EMAIL_DOMAINS")
    return {domain.strip().lower() for domain in raw.split(",") if domain.strip()}


def email_domain_allowed(email: str) -> bool:
    domains = allowed_domains()
    if not domains:
        return True
    return email.rsplit("@", 1)[-1].lower() in domains


def new_flow() -> dict:
    """Per-attempt secrets stored in the server-signed session."""
    return {
        "state": secrets.token_urlsafe(32),
        "nonce": secrets.token_urlsafe(32),
        "verifier": secrets.token_urlsafe(64),
        "ts": int(time.time()),
    }


def build_authorization_url(redirect_uri: str, flow: dict) -> str:
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(flow["verifier"].encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    params = {
        "client_id": _env("GOOGLE_CLIENT_ID"),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "state": flow["state"],
        "nonce": flow["nonce"],
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def exchange_code_for_claims(code: str, redirect_uri: str, flow: dict) -> dict:
    """Exchange the authorization code and return validated ID-token claims."""
    if time.time() - int(flow.get("ts", 0)) > FLOW_MAX_AGE_SECONDS:
        raise GoogleOAuthError("Sign-in attempt expired")

    body = urlencode(
        {
            "code": code,
            "client_id": _env("GOOGLE_CLIENT_ID"),
            "client_secret": _env("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": flow["verifier"],
        }
    ).encode("ascii")
    request = Request(
        TOKEN_ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            token_response = json.loads(response.read(262144).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        raise GoogleOAuthError("Token exchange failed")

    raw_id_token = token_response.get("id_token") if isinstance(token_response, dict) else None
    if not isinstance(raw_id_token, str):
        raise GoogleOAuthError("No ID token returned")

    try:
        # Google Auth verifies the JWT signature against Google's current
        # signing certificates and validates its audience, issuer, and expiry.
        # The certificates are fetched through the library's supported
        # transport, so rotated Google signing keys are picked up safely.
        claims = id_token.verify_oauth2_token(
            raw_id_token,
            GoogleAuthRequest(),
            _env("GOOGLE_CLIENT_ID"),
        )
    except (ValueError, GoogleAuthError) as exc:
        raise GoogleOAuthError("ID token verification failed") from exc

    if claims.get("iss") not in VALID_ISSUERS:
        raise GoogleOAuthError("Unexpected issuer")
    if not secrets.compare_digest(
        str(claims.get("nonce", "")).encode(),
        flow["nonce"].encode(),
    ):
        raise GoogleOAuthError("Nonce mismatch")
    email = claims.get("email")
    if not isinstance(email, str) or "@" not in email or len(email) > 254:
        raise GoogleOAuthError("No usable email")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleOAuthError("Email not verified by Google")
    if not claims.get("sub"):
        raise GoogleOAuthError("Missing subject")
    return claims
