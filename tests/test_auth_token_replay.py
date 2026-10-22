from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from backend.database import db


def test_auth_token_can_only_be_consumed_once_concurrently(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "_DB_PATH", str(tmp_path / "certificates.db"))
    db.init_db()
    assert db.create_user("token-user", "password-hash", "USER")
    user_id = db.get_user_by_username("token-user")["id"]
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    db.create_auth_token(user_id, "reset", "one-time-token", expires_at)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: db.consume_auth_token("one-time-token", "reset"), range(2)
        ))

    assert results.count(user_id) == 1
    assert results.count(None) == 1
