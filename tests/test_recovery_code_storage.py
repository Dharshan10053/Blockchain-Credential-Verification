import pytest

from backend.database import db


@pytest.mark.parametrize("stored_codes", ["{invalid json", "{\"code\": \"hash\"}"])
def test_malformed_recovery_code_storage_fails_closed(
    monkeypatch, tmp_path, stored_codes
):
    monkeypatch.setattr(db, "_DB_PATH", str(tmp_path / "certificates.db"))
    db.init_db()
    assert db.create_user("test-user", "password-hash", "USER")
    user = db.get_user_by_username("test-user")
    with db._connect() as connection:
        connection.execute(
            "UPDATE users SET recovery_codes = ? WHERE id = ?",
            (stored_codes, user["id"]),
        )

    assert not db.consume_recovery_code(user["id"], "hash")
