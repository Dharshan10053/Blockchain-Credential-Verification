import io
import hashlib
import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import app as app_module
from app import app
from backend.database import db as db_module
from backend.database.db import init_db, upsert_certificate
from backend.utils.blockchain import (
    Blockchain,
    BlockchainCorruptionError,
    migrate_legacy_text_ledger,
)


LEGACY_HASHES = (
    "964d22e8104e92df4983aee26ade62f7eda5ccdafd1804967b30681c864e5a7d",
    "bc4fb2bbb13c5c3e057f3164461763eb4cbd41c90cac555c8f91ce2a16985b32",
    "9bdd4073ba0bc39948ce36e42eed44a862049ae6606c5612898aae046feff8f5",
    "5a2c75386441e621da2708c243f74eb66ce985e4bc5389f7585d5ce710b8a25a",
    "7ba6cf5dba4795222f691ef8284ef1d758e67f0eb7be56e472d042a8028b672a",
)
SQLITE_MATCHED_HASHES = LEGACY_HASHES[2:]


def _isolated_database(monkeypatch, path):
    monkeypatch.setattr(db_module, "_DB_PATH", str(path))
    init_db()


def _csrf_token(client, route):
    response = client.get(route)
    match = re.search(
        r'name="csrf_token"[^>]*value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return match.group(1)


def _legacy_fixture(tmp_path):
    archive = tmp_path / "blockchain.txt"
    archive.write_text("\n".join(LEGACY_HASHES) + "\n", encoding="utf-8")
    chain_path = tmp_path / "blockchain.json"
    return archive, chain_path


def test_legacy_migration_preserves_exact_hashes_once_and_is_idempotent(tmp_path):
    archive, chain_path = _legacy_fixture(tmp_path)
    original_archive = archive.read_bytes()
    initial = Blockchain(chain_path)
    assert len(initial.chain) == 1

    first = migrate_legacy_text_ledger(chain_path, archive)
    migrated = Blockchain(chain_path)
    second = migrate_legacy_text_ledger(chain_path, archive)
    reloaded = Blockchain(chain_path)
    assert reloaded.add_certificate_if_absent("f" * 64)
    post_issuance = Blockchain(chain_path)
    repeated_after_issue = migrate_legacy_text_ledger(chain_path, archive)

    assert first["migrated"] is True
    assert first["hashes"] == 5
    assert first["added"] == 5
    assert first["backup"]
    assert Path(first["backup"]).read_bytes()
    assert second["migrated"] is False
    assert second["added"] == 0
    assert repeated_after_issue["migrated"] is False
    assert len(migrated.chain) == 6
    assert sum(block["data"] == "Genesis Block" for block in migrated.chain) == 1
    assert [block["data"]["hash"] for block in migrated.chain[1:]] == list(LEGACY_HASHES)
    assert len(migrated.find_all_hashes()) == 5
    assert migrated.is_valid() and reloaded.is_valid()
    assert post_issuance.find_all_hashes() == set(LEGACY_HASHES) | {"f" * 64}
    assert archive.read_bytes() == original_archive

    for cert_hash in LEGACY_HASHES[:2]:
        assert migrated.find_by_hash(cert_hash)["data"] == {
            "hash": cert_hash,
            "legacy": True,
            "source": "blockchain.txt",
        }


def test_invalid_legacy_source_does_not_overwrite_existing_chain(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    chain = Blockchain(chain_path)
    original = chain_path.read_bytes()
    archive = tmp_path / "blockchain.txt"
    archive.write_text("not-a-certificate-hash\n", encoding="utf-8")

    with pytest.raises(BlockchainCorruptionError):
        migrate_legacy_text_ledger(chain_path, archive)

    assert chain_path.read_bytes() == original


@pytest.mark.parametrize("genesis_format", ["backend", "top-level"])
def test_migration_normalizes_only_known_old_genesis_and_backs_it_up(
    tmp_path, genesis_format
):
    archive, chain_path = _legacy_fixture(tmp_path)
    timestamp = "2026-03-03T12:12:52.018845Z"
    old_genesis = {
        "index": 0,
        "timestamp": timestamp,
        "data": "Genesis Block",
        "previous_hash": "0",
        "hash": (
            Blockchain._compute_hash(0, "", "Genesis Block", "0")
            if genesis_format == "backend"
            else hashlib.sha256(
                f"0{timestamp}Genesis Block0".encode()
            ).hexdigest()
        ),
    }
    original_payload = {
        "chain": [old_genesis],
        "updated_at": "2026-03-03T12:29:47.276326Z",
    }
    chain_path.write_text(json.dumps(original_payload), encoding="utf-8")
    original_bytes = chain_path.read_bytes()

    result = migrate_legacy_text_ledger(chain_path, archive)
    chain = Blockchain(chain_path)

    assert result["genesis_normalized"] is True
    assert Path(result["backup"]).read_bytes() == original_bytes
    assert chain.chain[0]["timestamp"] == timestamp
    assert chain.chain[0]["hash"] == Blockchain._compute_hash(
        0, timestamp, "Genesis Block", "0"
    )
    assert chain.is_valid()


def test_existing_sqlite_matched_hashes_reproduce_live_hash_without_writing():
    database_path = Path(db_module._DB_PATH).resolve()
    if not database_path.exists():
        pytest.skip("The local ignored certificate database is not available.")
    database_uri = database_path.as_uri() + "?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    try:
        rows = connection.execute(
            """
            SELECT cert_hash, name, course, organization, date, cert_id
            FROM certificates
            WHERE cert_hash IN (?, ?, ?)
            """,
            SQLITE_MATCHED_HASHES,
        ).fetchall()
    finally:
        connection.close()

    assert {row[0] for row in rows} == set(SQLITE_MATCHED_HASHES)
    for cert_hash, name, course, university, date, cert_id in rows:
        calculated = app_module.generate_hash({
            "name": name,
            "course": course,
            "university": university,
            "date": date,
            "cert_id": cert_id,
        })
        assert calculated == cert_hash


@pytest.mark.parametrize(
    "mutate",
    [
        lambda chain: chain[1]["data"].update({"course": "tampered"}),
        lambda chain: chain[1].update({"previous_hash": "0" * 64}),
        lambda chain: chain[1].update({"hash": "0" * 64}),
        lambda chain: chain[1].update({"index": 3}),
        lambda chain: chain[1]["data"].update({"hash": "malformed"}),
        lambda chain: chain[0].update({"data": "not genesis"}),
    ],
)
def test_tampering_with_data_links_or_hash_invalidates_chain(tmp_path, mutate):
    chain = Blockchain(tmp_path / "blockchain.json")
    chain.add_certificate_if_absent("a" * 64, {"name": "Original"})
    mutate(chain.chain)
    assert not chain.is_valid()


def test_migration_rejects_duplicate_certificate_hashes_in_chain(tmp_path):
    archive, chain_path = _legacy_fixture(tmp_path)
    chain = Blockchain(chain_path)
    chain.add_certificate_if_absent(LEGACY_HASHES[0], {"name": "Existing"})
    result = migrate_legacy_text_ledger(chain_path, archive)
    migrated = Blockchain(chain_path)
    assert result["added"] == 4
    assert len(migrated.find_all_hashes()) == 5
    assert len(migrated.chain) == 6
    assert migrated.find_by_hash(LEGACY_HASHES[0])["data"] == {
        "hash": LEGACY_HASHES[0],
        "name": "Existing",
    }


def test_concurrent_issuance_appends_a_hash_only_once(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    Blockchain(chain_path)

    def issue():
        return Blockchain(chain_path).add_certificate_if_absent("e" * 64)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _index: issue(), range(8)))

    assert results.count(True) == 1
    chain = Blockchain(chain_path)
    assert chain.find_all_hashes() == {"e" * 64}
    assert chain.is_valid()


def test_browser_and_api_verification_find_migrated_hash_after_reload(
    monkeypatch, tmp_path
):
    archive, chain_path = _legacy_fixture(tmp_path)
    migrate_legacy_text_ledger(chain_path, archive)
    monkeypatch.setitem(app.config, "BLOCKCHAIN_PATH", str(chain_path))
    details = {
        "name": "Legacy Holder",
        "course": "Legacy Course",
        "university": "Legacy University",
        "date": "2024",
        "cert_id": "LEGACY-001",
    }
    cert_hash = LEGACY_HASHES[0]
    monkeypatch.setattr(app_module, "perform_ocr", lambda filepath: "legacy fixture")
    monkeypatch.setattr(app_module, "extract_details", lambda text: details)
    monkeypatch.setattr(app_module, "generate_hash", lambda extracted: cert_hash)

    with app.test_client() as client:
        browser_token = _csrf_token(client, "/verify")
        browser = client.post(
            "/verify",
            data={
                "csrf_token": browser_token,
                "certificate": (io.BytesIO(b"certificate"), "certificate.png"),
            },
            content_type="multipart/form-data",
        )
        api = client.post(
            "/api/verify",
            data={"certificate": (io.BytesIO(b"certificate"), "certificate.png")},
            content_type="multipart/form-data",
        )

    assert browser.status_code == 200
    assert b"Certificate Verified" in browser.data
    assert api.status_code == 200
    assert api.get_json()["status"] == "VERIFIED"
    assert Blockchain(chain_path).find_by_hash(cert_hash)


def test_ledger_and_api_blockchain_use_the_same_canonical_membership(
    monkeypatch, tmp_path
):
    archive, chain_path = _legacy_fixture(tmp_path)
    migrate_legacy_text_ledger(chain_path, archive)
    monkeypatch.setitem(app.config, "BLOCKCHAIN_PATH", str(chain_path))
    monkeypatch.setattr(app_module, "ADMIN_API_KEY", "migration-test-admin-key")
    _isolated_database(monkeypatch, tmp_path / "ledger.db")

    with app.test_client() as client:
        headers = {"X-Admin-Key": "migration-test-admin-key"}
        ledger_response = client.get("/ledger", headers=headers)
        api_response = client.get("/api/blockchain", headers=headers)

    api_chain = api_response.get_json()
    assert ledger_response.status_code == 200
    assert api_response.status_code == 200
    assert api_chain["valid"] is True
    assert set(
        block["data"]["hash"]
        for block in api_chain["chain"][1:]
    ) == set(LEGACY_HASHES)
    assert all(cert_hash.encode() in ledger_response.data for cert_hash in LEGACY_HASHES)


def test_report_status_uses_canonical_membership_not_sqlite_presence(
    monkeypatch, tmp_path
):
    chain_path = tmp_path / "blockchain.json"
    Blockchain(chain_path)
    monkeypatch.setitem(app.config, "BLOCKCHAIN_PATH", str(chain_path))
    _isolated_database(monkeypatch, tmp_path / "report.db")
    cert_hash = "f" * 64
    token = upsert_certificate(
        cert_hash,
        {
            "name": "Metadata Only",
            "course": "Not on chain",
            "issuing_authority": "Test",
            "date": "2026",
            "certificate_id": "META-ONLY",
        },
        action="ISSUE",
    )
    report_path = tmp_path / "report.pdf"
    report_path.write_bytes(b"test report")
    captured_result = {}

    def capture_report(result, base_url=None):
        captured_result.update(result)
        return str(report_path)

    monkeypatch.setattr(app_module, "generate_report", capture_report)
    with app.test_client() as client:
        response = client.get(f"/report/{cert_hash}?token={token}")

    assert response.status_code == 200
    assert captured_result["status"] == "FAKE"
    assert captured_result["label"] == "NOT VERIFIED"
    assert captured_result["blockchain_status"] == (
        "NOT VERIFIED - hash not found on the canonical ledger"
    )
