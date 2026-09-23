import io
import re

import fitz

import app as app_module
from app import app
from backend.database import db
from werkzeug.security import generate_password_hash


def _post_issue(client):
    """POST to /issue using an already-authenticated client."""
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
    store_path = tmp_path / "blockchain.txt"
    database_path = tmp_path / "certificates.db"
    details = {
        "name": "Report Holder",
        "course": "Secure Systems",
        "date": "September 8, 2026",
        "cert_id": "REPORT-001",
        "university": "CertAuth Institute",
    }
    cert_hash = "d" * 64

    monkeypatch.setattr(app_module, "BLOCKCHAIN_FILE", str(store_path))
    monkeypatch.setattr(db, "_DB_PATH", str(database_path))
    monkeypatch.setattr(app_module, "perform_ocr", lambda filepath: "report fixture")
    monkeypatch.setattr(app_module, "extract_details", lambda text: details)
    monkeypatch.setattr(app_module, "generate_hash", lambda extracted: cert_hash)

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        # Create admin user and authenticate via session
        with app.app_context():
            db.init_db()
            db.create_user("report_admin", generate_password_hash("password"), "ADMIN")
        client.post("/login", data={"username": "report_admin", "password": "password"})

        issue_response = _post_issue(client)
        assert issue_response.status_code == 200
        assert b"Certificate Issued" in issue_response.data

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
        cert_hash,
        "Verification Timestamp",
    ):
        assert expected.lower() in normalized_pdf_text

    assert "Alice Standard" not in pdf_text
    assert "Bob Legacy" not in pdf_text
