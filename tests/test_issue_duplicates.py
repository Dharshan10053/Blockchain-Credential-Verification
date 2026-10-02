import io
import re
import uuid

import app as app_module
from app import app
from backend.database import db as db_module
from backend.database.db import create_user, init_db
from backend.utils.blockchain import Blockchain
from werkzeug.security import generate_password_hash


def _set_chain_path(monkeypatch, path):
    monkeypatch.setitem(app.config, "BLOCKCHAIN_PATH", str(path))


def _set_db_path(monkeypatch, path):
    monkeypatch.setattr(db_module, "_DB_PATH", str(path))


def _chain_hashes(path):
    chain = Blockchain(path)
    return [block["data"]["hash"] for block in chain.chain[1:]]


def _login_as_role(client, role):
    client.environ_base["REMOTE_ADDR"] = f"198.51.100.{uuid.uuid4().int % 250 + 1}"
    login_page = client.get("/login")
    token = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        login_page.get_data(as_text=True),
    ).group(1)
    username = f"issue-{role.lower()}-{uuid.uuid4().hex}"
    password = "correct horse battery"
    init_db()
    assert create_user(username, generate_password_hash(password), role)
    response = client.post(
        "/login",
        data={"csrf_token": token, "username": username, "password": password},
    )
    assert response.status_code == 302


def _post_issue(client, details, cert_hash):
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


def test_api_issue_requires_admin_key_and_rejects_duplicate(
    monkeypatch, tmp_path
):
    store_path = tmp_path / "blockchain.json"
    cert_hash = "a" * 64
    details = {
        "name": "Fresh Tester",
        "course": "Testing",
        "date": "2026-09-08",
        "cert_id": "FRESH-TEST-001",
        "university": "CertAuth",
    }

    _set_chain_path(monkeypatch, store_path)
    _set_db_path(monkeypatch, tmp_path / "browser-issue.db")
    monkeypatch.setattr(app_module, "_process_upload", lambda file: (details, cert_hash))

    with app.test_client() as client:
        first = client.post(
            "/api/issue",
            data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
            content_type="multipart/form-data",
        )
        assert first.status_code == 403
        rejected_key = client.post(
            "/api/issue",
            data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
            content_type="multipart/form-data",
            headers={"X-Admin-Key": "invalid-admin-key"},
        )
        assert rejected_key.status_code == 403
        first = client.post(
            "/api/issue",
            data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
            content_type="multipart/form-data",
            headers={"X-Admin-Key": "test-admin-key-12345"},
        )
        second = client.post(
            "/api/issue",
            data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
            content_type="multipart/form-data",
            headers={"X-Admin-Key": "test-admin-key-12345"},
        )

    assert first.status_code == 200
    assert first.get_json()["status"] == "ISSUED SUCCESSFULLY"
    assert second.status_code == 200
    assert second.get_json()["status"] == "ALREADY EXISTS"
    assert _chain_hashes(store_path) == [cert_hash]


def test_browser_issue_flow_persists_duplicate_detection_across_restart(
    monkeypatch, tmp_path
):
    store_path = tmp_path / "blockchain.json"
    details = {
        "name": "Browser Tester",
        "course": "Browser Testing",
        "date": "2026-09-08",
        "cert_id": "BROWSER-TEST-001",
        "university": "CertAuth",
    }
    first_hash = "b" * 64
    second_hash = "c" * 64
    current = {"hash": first_hash}

    _set_chain_path(monkeypatch, store_path)
    _set_db_path(monkeypatch, tmp_path / "admin-issue.db")
    monkeypatch.setattr(
        app_module,
        "perform_ocr",
        lambda filepath: "browser fixture OCR text",
    )
    monkeypatch.setattr(
        app_module,
        "extract_details",
        lambda text: details,
    )
    monkeypatch.setattr(
        app_module,
        "generate_hash",
        lambda extracted_details: current["hash"],
    )

    with app.test_client() as client:
        _login_as_role(client, "VERIFIER")
        first = _post_issue(client, details, first_hash)
        duplicate = _post_issue(client, details, first_hash)

    with app.test_client() as restarted_client:
        _login_as_role(restarted_client, "VERIFIER")
        persisted_duplicate = _post_issue(restarted_client, details, first_hash)
        current["hash"] = second_hash
        different = _post_issue(restarted_client, details, second_hash)

    assert first.status_code == 200
    assert b"Certificate Issued" in first.data
    assert b"Already Issued" not in first.data
    assert duplicate.status_code == 200
    assert b"Already Issued" in duplicate.data
    assert persisted_duplicate.status_code == 200
    assert b"Already Issued" in persisted_duplicate.data
    assert different.status_code == 200
    assert b"Already Issued" not in different.data
    assert _chain_hashes(store_path) == [first_hash, second_hash]


def test_unauthenticated_browser_issue_is_rejected(monkeypatch, tmp_path):
    store_path = tmp_path / "blockchain.json"
    _set_chain_path(monkeypatch, store_path)
    client = app.test_client()
    client.environ_base["REMOTE_ADDR"] = f"198.51.100.{uuid.uuid4().int % 250 + 1}"

    response = client.get("/issue")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=/issue")
    login_page = client.get("/login")
    csrf_token = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        login_page.get_data(as_text=True),
    ).group(1)
    post_response = client.post(
        "/issue",
        data={
            "csrf_token": csrf_token,
            "certificate": (io.BytesIO(b"certificate"), "certificate.png"),
        },
        content_type="multipart/form-data",
    )
    assert post_response.status_code == 302
    assert post_response.headers["Location"].endswith("/login?next=/issue")
    assert not store_path.exists()


def test_admin_session_can_issue_through_browser_route(monkeypatch, tmp_path):
    store_path = tmp_path / "blockchain.json"
    details = {
        "name": "Admin Tester",
        "course": "Admin Testing",
        "date": "2026-09-08",
        "cert_id": "ADMIN-ISSUE-001",
        "university": "CertAuth",
    }
    _set_chain_path(monkeypatch, store_path)
    _set_db_path(monkeypatch, tmp_path / "admin-browser-issue.db")
    monkeypatch.setattr(app_module, "perform_ocr", lambda filepath: "admin fixture OCR text")
    monkeypatch.setattr(app_module, "extract_details", lambda text: details)
    monkeypatch.setattr(app_module, "generate_hash", lambda extracted: "d" * 64)

    with app.test_client() as client:
        _login_as_role(client, "ADMIN")
        response = _post_issue(client, details, "d" * 64)

    assert response.status_code == 200
    assert b"Certificate Issued" in response.data
    assert _chain_hashes(store_path) == ["d" * 64]


def test_unauthenticated_api_issue_is_rejected(monkeypatch):
    called = False

    def process_upload(file):
        nonlocal called
        called = True
        return {}, "e" * 64

    monkeypatch.setattr(app_module, "_process_upload", process_upload)
    response = app.test_client().post(
        "/api/issue",
        data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 403
    assert not called


def test_issue_form_has_no_api_key_field():
    with app.test_client() as client:
        _login_as_role(client, "VERIFIER")
        response = client.get("/issue")

    assert response.status_code == 200
    assert b"Admin API Key" not in response.data
    assert b'name="admin_key"' not in response.data
