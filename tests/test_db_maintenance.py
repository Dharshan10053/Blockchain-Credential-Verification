import pytest

from backend.database import db


def test_archive_old_logs_rejects_negative_retention_without_deleting(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "_DB_PATH", str(tmp_path / "certificates.db"))
    db.init_db()
    db.log_verification("VERIFY", "hash", "VERIFIED")

    with pytest.raises(ValueError, match="days_to_keep must be non-negative"):
        db.archive_old_logs(-1)

    with db._connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 1
