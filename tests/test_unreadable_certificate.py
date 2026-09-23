"""
Tests for the unreadable-certificate extraction gate.

Covers:
  * a clearly readable certificate -> existing issue/verify flow succeeds
  * unreadable / empty extraction  -> rejected with the new message
  * insufficient certificate details -> rejected
  * no blockchain or database record is created for a rejected upload

The OCR/text-extraction stage (perform_ocr) is stubbed so the tests exercise
the validation gate deterministically, without Tesseract/Poppler binaries or
sample image fixtures.
"""
import io
import os

os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-extraction-gate-tests")

import pytest

import app as app_module
from backend.database import db as db_module
from backend.utils.extraction_quality import (
    UNREADABLE_CERTIFICATE_MESSAGE,
    assess_extraction,
)

READABLE_CERTIFICATE_TEXT = """
ACME TRAINING ACADEMY
Certificate of Completion
This is to certify that
Priya Sharma
has successfully completed the course
Advanced Data Analytics
Date of Issue: 12 March 2024
Certificate No: ACME-2024-889210
"""

# Dense OCR noise from an unreadable/blurry scan: vowel-less consonant runs
# and symbol soup, with no recoverable certificate information.
NOISY_OCR_TEXT = (
    "~|} xkq zzt >< bkgd ]][[ mnbvc ;;; wrtzp %^&* lkjhg ||| zxcvbn ### "
    "qwrtp \\\\ hgfdz //// ptkmn <<>> vbnmq @@@ trwqz {{}} klmnp !!! "
)

# Extraction that reads cleanly but contains no certificate information.
NO_DETAILS_TEXT = (
    "The quick brown fox jumps over the lazy dog while the weather outside "
    "remains pleasant and the afternoon passes quietly without any events "
    "of note occurring anywhere near the river."
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client with CSRF/rate limiting off and isolated storage."""
    app_module.app.config["TESTING"] = True
    app_module.app.config["WTF_CSRF_ENABLED"] = False
    monkeypatch.setattr(
        app_module, "BLOCKCHAIN_FILE", str(tmp_path / "blockchain.txt")
    )
    monkeypatch.setattr(
        app_module, "UPLOAD_FOLDER", str(tmp_path / "uploads"), raising=False
    )
    os.makedirs(tmp_path / "uploads", exist_ok=True)
    monkeypatch.setattr(db_module, "_DB_PATH", str(tmp_path / "certificates.db"))
    app_module.limiter.enabled = False
    try:
        with app_module.app.test_client() as test_client:
            yield test_client
    finally:
        app_module.limiter.enabled = True


def _upload(client, url, text, monkeypatch, filename="certificate.png"):
    """POST a dummy file with perform_ocr stubbed to return `text`."""
    monkeypatch.setattr(app_module, "perform_ocr", lambda filepath: text)
    return client.post(
        url,
        data={"certificate": (io.BytesIO(b"dummy-image-bytes"), filename)},
        content_type="multipart/form-data",
    )


def _stored_hashes(client):
    if not os.path.exists(app_module.BLOCKCHAIN_FILE):
        return []
    with open(app_module.BLOCKCHAIN_FILE) as handle:
        return [line for line in handle.read().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Unit-level: the quality assessment itself
# ---------------------------------------------------------------------------

def test_readable_text_passes_assessment():
    details = app_module.extract_details(READABLE_CERTIFICATE_TEXT)
    readable, reason = assess_extraction(READABLE_CERTIFICATE_TEXT, details)
    assert readable is True
    assert reason == "ok"


@pytest.mark.parametrize(
    "text, expected_reason",
    [
        ("", "empty_or_near_empty_text"),
        ("   \n\n  ", "empty_or_near_empty_text"),
        ("Cert", "empty_or_near_empty_text"),
        (NOISY_OCR_TEXT, "noisy_ocr_text"),
    ],
)
def test_unusable_text_fails_assessment(text, expected_reason):
    details = app_module.extract_details(text)
    readable, reason = assess_extraction(text, details)
    assert readable is False
    assert reason == expected_reason


def test_clean_text_without_certificate_details_is_rejected():
    details = app_module.extract_details(NO_DETAILS_TEXT)
    readable, reason = assess_extraction(NO_DETAILS_TEXT, details)
    assert readable is False
    assert reason == "insufficient_certificate_details"


def test_imperfect_ocr_with_enough_fields_is_still_accepted():
    """Legitimate certificate with messy OCR must not be rejected."""
    imperfect = (
        "ACME TRAINlNG ACADEMY ~\n"
        "Certificate of Completi0n |\n"
        "This is to certify that\n"
        "Priya Sharma\n"
        "has successfully completed the course\n"
        "Advanced Data Analyt1cs ;;\n"
        "Date of Issue: 12 March 2024\n"
        "Certificate No: ACME-2024-889210\n"
    )
    details = app_module.extract_details(imperfect)
    readable, _ = assess_extraction(imperfect, details)
    assert readable is True


# ---------------------------------------------------------------------------
# Route-level: /issue
# ---------------------------------------------------------------------------

def test_issue_succeeds_for_readable_certificate(client, monkeypatch):
    response = _upload(client, "/issue", READABLE_CERTIFICATE_TEXT, monkeypatch)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert UNREADABLE_CERTIFICATE_MESSAGE not in body
    assert "Priya Sharma" in body
    assert len(_stored_hashes(client)) == 1


@pytest.mark.parametrize("text", ["", NOISY_OCR_TEXT, NO_DETAILS_TEXT])
def test_issue_rejects_unreadable_certificate(client, monkeypatch, text):
    response = _upload(client, "/issue", text, monkeypatch)
    assert response.status_code == 400
    assert UNREADABLE_CERTIFICATE_MESSAGE in response.get_data(as_text=True)


def test_rejected_issue_creates_no_blockchain_or_db_record(client, monkeypatch):
    response = _upload(client, "/issue", NOISY_OCR_TEXT, monkeypatch)
    assert response.status_code == 400
    assert _stored_hashes(client) == []
    if os.path.exists(db_module._DB_PATH):
        db_module.init_db()
        assert db_module.get_all_certificates() == []


# ---------------------------------------------------------------------------
# Route-level: /verify
# ---------------------------------------------------------------------------

def test_verify_still_processes_readable_certificate(client, monkeypatch):
    response = _upload(client, "/verify", READABLE_CERTIFICATE_TEXT, monkeypatch)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert UNREADABLE_CERTIFICATE_MESSAGE not in body
    assert "Priya Sharma" in body


def test_issued_certificate_verifies_successfully(client, monkeypatch):
    issued = _upload(client, "/issue", READABLE_CERTIFICATE_TEXT, monkeypatch)
    assert issued.status_code == 200
    verified = _upload(client, "/verify", READABLE_CERTIFICATE_TEXT, monkeypatch)
    assert verified.status_code == 200
    body = verified.get_data(as_text=True)
    assert "Certificate Verified" in body
    assert "status-verified" in body


@pytest.mark.parametrize("text", ["", NOISY_OCR_TEXT, NO_DETAILS_TEXT])
def test_verify_rejects_unreadable_certificate(client, monkeypatch, text):
    response = _upload(client, "/verify", text, monkeypatch)
    assert response.status_code == 400
    assert UNREADABLE_CERTIFICATE_MESSAGE in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Route-level: JSON API
# ---------------------------------------------------------------------------

def test_api_issue_succeeds_for_readable_certificate(client, monkeypatch):
    response = _upload(client, "/api/issue", READABLE_CERTIFICATE_TEXT, monkeypatch)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ISSUED SUCCESSFULLY"
    assert payload["name"] == "Priya Sharma"


@pytest.mark.parametrize("url", ["/api/issue", "/api/verify"])
@pytest.mark.parametrize("text", ["", NOISY_OCR_TEXT, NO_DETAILS_TEXT])
def test_api_rejects_unreadable_certificate(client, monkeypatch, url, text):
    response = _upload(client, url, text, monkeypatch)
    assert response.status_code == 400
    assert response.get_json()["error"] == UNREADABLE_CERTIFICATE_MESSAGE
    assert _stored_hashes(client) == []


def test_invalid_file_type_still_rejected_before_extraction(client, monkeypatch):
    response = _upload(
        client, "/api/issue", READABLE_CERTIFICATE_TEXT, monkeypatch,
        filename="certificate.exe",
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid file type"
