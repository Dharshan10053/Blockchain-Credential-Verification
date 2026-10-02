import io
import re
import uuid

import fitz
from werkzeug.security import generate_password_hash

import app as app_module
from app import app
from backend.database import db
from backend.database.db import create_user, get_user_by_username, init_db
from backend.utils.blockchain import Blockchain


def _post_issue(client):
    form = client.get("/issue")
    token = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        form.get_data(as_text=True),
    ).group(1)
    return client.post(
        "/issue",
        data={
            "csrf_token": token,
            "certificate": (io.BytesIO(b"certificate"), "certificate.png"),
        },
        content_type="multipart/form-data",
    )


def _post_verify(client):
    form = client.get("/verify")
    token = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        form.get_data(as_text=True),
    ).group(1)
    return client.post(
        "/verify",
        data={
            "csrf_token": token,
            "certificate": (io.BytesIO(b"certificate"), "certificate.png"),
        },
        content_type="multipart/form-data",
    )


def test_browser_issue_verify_report_contains_certificate_metadata(monkeypatch, tmp_path):
    store_path = tmp_path / "blockchain.json"
    database_path = tmp_path / "certificates.db"
    details = {
        "name": "Report Holder",
        "course": "Secure Systems",
        "date": "September 8, 2026",
        "cert_id": "REPORT-001",
        "university": "CertAuth Institute",
    }
    cert_hash = "d" * 64

    monkeypatch.setitem(app_module.app.config, "BLOCKCHAIN_PATH", str(store_path))
    monkeypatch.setattr(db, "_DB_PATH", str(database_path))
    monkeypatch.setattr(app_module, "perform_ocr", lambda filepath: "report fixture")
    monkeypatch.setattr(app_module, "extract_details", lambda text: details)
    monkeypatch.setattr(app_module, "generate_hash", lambda extracted: cert_hash)
    with app.test_client() as client:
        init_db()
        username = f"report-verifier-{uuid.uuid4().hex}"
        assert create_user(username, generate_password_hash("test password"), "VERIFIER")
        user = get_user_by_username(username)
        with client.session_transaction() as user_session:
            user_session["user_id"] = user["id"]
            user_session["auth_version"] = user["auth_version"]
        issue_response = _post_issue(client)
        assert issue_response.status_code == 200
        assert b"Certificate Issued" in issue_response.data
        assert Blockchain(store_path).find_by_hash(cert_hash)

        verify_response = _post_verify(client)
        assert verify_response.status_code == 200
        assert b"Certificate Verified" in verify_response.data

        report_response = client.get(f"/report/{cert_hash}")

    assert report_response.status_code == 200
    assert report_response.mimetype == "application/pdf"
    document = fitz.open(stream=report_response.data, filetype="pdf")
    pdf_text = "\n".join(page.get_text() for page in document)
    normalized_pdf_text = pdf_text.lower()

    for expected in (
        "Certificate Verification",
        "VERIFIED",
        details["name"],
        details["course"],
        details["date"],
        details["cert_id"],
        details["university"],
        "Blockchain Status",
        "VERIFIED - hash found on the canonical ledger",
        cert_hash,
        "Verification Timestamp",
    ):
        assert expected.lower() in normalized_pdf_text

    assert "Alice Standard" not in pdf_text
    assert "Bob Legacy" not in pdf_text
