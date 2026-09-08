import io
import re

import app as app_module
from app import app


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


def test_api_issue_accepts_new_certificate_and_rejects_duplicate_without_api_key(
    monkeypatch, tmp_path
):
    store_path = tmp_path / "blockchain.txt"
    cert_hash = "a" * 64
    details = {
        "name": "Fresh Tester",
        "course": "Testing",
        "date": "2026-09-08",
        "cert_id": "FRESH-TEST-001",
        "university": "CertAuth",
    }

    monkeypatch.setattr(app_module, "BLOCKCHAIN_FILE", str(store_path))
    monkeypatch.setattr(app_module, "_process_upload", lambda file: (details, cert_hash))

    with app.test_client() as client:
        first = client.post(
            "/api/issue",
            data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
            content_type="multipart/form-data",
        )
        second = client.post(
            "/api/issue",
            data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
            content_type="multipart/form-data",
        )

    assert first.status_code == 200
    assert first.get_json()["status"] == "ISSUED SUCCESSFULLY"
    assert second.status_code == 200
    assert second.get_json()["status"] == "ALREADY EXISTS"
    assert store_path.read_text().splitlines() == [cert_hash]


def test_browser_issue_flow_persists_duplicate_detection_across_restart(
    monkeypatch, tmp_path
):
    store_path = tmp_path / "blockchain.txt"
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

    monkeypatch.setattr(app_module, "BLOCKCHAIN_FILE", str(store_path))
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
        first = _post_issue(client, details, first_hash)
        duplicate = _post_issue(client, details, first_hash)

    with app.test_client() as restarted_client:
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
    assert store_path.read_text().splitlines() == [first_hash, second_hash]


def test_issue_form_has_no_api_key_field():
    with app.test_client() as client:
        response = client.get("/issue")

    assert response.status_code == 200
    assert b"Admin API Key" not in response.data
    assert b'name="admin_key"' not in response.data
