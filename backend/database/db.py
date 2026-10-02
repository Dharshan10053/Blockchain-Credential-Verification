"""
SQLite persistence layer.
"""
from __future__ import annotations
import logging
import os
import sqlite3
import uuid
import hashlib
import json
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "certificates.db")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                cert_hash    TEXT    UNIQUE NOT NULL,
                cert_id      TEXT,
                name         TEXT,
                course       TEXT,
                organization TEXT,
                date         TEXT,
                action       TEXT,
                created_at   TEXT NOT NULL
            )
        """)
        
        # Add issuing_authority column for backward compatibility/migration
        try:
            conn.execute("ALTER TABLE certificates ADD COLUMN issuing_authority TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        # Add verification_token column for signed token URLs
        try:
            conn.execute("ALTER TABLE certificates ADD COLUMN verification_token TEXT")
        except sqlite3.OperationalError:
            pass # Column already exists

        # Create audit_logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT NOT NULL,
                action_type  TEXT NOT NULL,
                cert_hash    TEXT,
                outcome      TEXT NOT NULL,
                ip_address   TEXT,
                user_agent   TEXT,
                details      TEXT
            )
        """)
        
        # Add performance indices
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cert_hash ON certificates(cert_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_token ON certificates(verification_token)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'VERIFIER',
                email_verified INTEGER NOT NULL DEFAULT 0,
                -- TOTP secrets are stored in plaintext because this project has
                -- no key-management dependency (no `cryptography`/KMS) and a
                -- home-grown cipher would be worse than the honest limitation.
                -- Anyone able to read this database file can therefore generate
                -- valid TOTP codes; protect the file with OS permissions and
                -- backups, and migrate to column-level encryption (or a KMS)
                -- before treating database read access as non-sensitive.
                totp_secret TEXT,
                totp_enabled INTEGER NOT NULL DEFAULT 0,
                -- JSON array of SHA-256 recovery-code hashes; never the codes.
                recovery_codes TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                auth_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)
        added_columns = set()
        for column, definition in (
            ("email", "TEXT"), ("email_verified", "INTEGER NOT NULL DEFAULT 0"),
            ("totp_secret", "TEXT"), ("totp_enabled", "INTEGER NOT NULL DEFAULT 0"),
            ("recovery_codes", "TEXT"), ("is_active", "INTEGER NOT NULL DEFAULT 1"),
            ("auth_version", "INTEGER NOT NULL DEFAULT 0"),
            ("last_login", "TEXT"),
        ):
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
                added_columns.add(column)
            except sqlite3.OperationalError:
                pass
        if "email_verified" in added_columns:
            # Migration for accounts that predate email verification. The new
            # column defaults to "unverified", which would lock every existing
            # account out of /login. Those users were never asked to verify an
            # address, so they keep their previous (working) login behaviour;
            # only accounts created from now on must confirm their email.
            conn.execute("UPDATE users SET email_verified = 1 WHERE email_verified = 0")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                purpose TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_token_hash ON auth_tokens(token_hash)")
        
        conn.commit()
    logger.info("Database initialised at %s", _DB_PATH)


def upsert_certificate(cert_hash: str, details: dict, action: str = "VERIFY") -> str:
    now = datetime.now(timezone.utc).isoformat()
    
    # Robust fallback logic for all fields
    def _get(keys, default=""):
        for k in keys:
            val = details.get(k)
            if val and str(val).strip() and str(val).strip().lower() != "not extracted":
                return str(val).strip()
        return default

    org = _get(["issuing_authority", "organization", "issuer", "institution", "issued_by"])
    course = _get(["course", "certificate_title", "course_title", "title", "course_name", "certification", "program"])
    name = _get(["name", "candidate_name", "student_name", "recipient"])
    cert_id = _get(["cert_id", "certificate_id", "id", "credential_id"])
    date_val = _get(["date", "issue_date", "year", "completion_date", "issued_on"])
    
    with _connect() as conn:
        # Check if it already exists to preserve its token
        row = conn.execute("SELECT verification_token FROM certificates WHERE cert_hash = ?", (cert_hash,)).fetchone()
        token = row["verification_token"] if (row and row["verification_token"]) else str(uuid.uuid4())
        
        conn.execute("""
            INSERT INTO certificates (cert_hash, cert_id, name, course, organization, issuing_authority, date, action, created_at, verification_token)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cert_hash) DO UPDATE SET
                action     = excluded.action,
                created_at = excluded.created_at,
                organization = excluded.organization,
                issuing_authority = excluded.issuing_authority,
                course = excluded.course,
                name = excluded.name,
                date = excluded.date,
                cert_id = excluded.cert_id
        """, (
            cert_hash,
            cert_id,
            name,
            course,
            org,
            org,
            date_val,
            action,
            now,
            token
        ))
        conn.commit()
        return token


def get_all_certificates() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM certificates ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_certificate_by_hash(cert_hash: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM certificates WHERE cert_hash = ?", (cert_hash,)).fetchone()
    return dict(row) if row else None


def get_certificate_by_token(token: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM certificates WHERE verification_token = ?", (token,)).fetchone()
    return dict(row) if row else None


def log_verification(action_type: str, cert_hash: str, outcome: str, ip_address: str = "", user_agent: str = "", details: str = ""):
    """Log verification details for audit and fraud analytics."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute("""
            INSERT INTO audit_logs (timestamp, action_type, cert_hash, outcome, ip_address, user_agent, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (now, action_type, cert_hash, outcome, ip_address, user_agent, details))
        conn.commit()

def archive_old_logs(days_to_keep: int = 90):
    """Delete audit logs older than the specified number of days to prevent database bloat."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).isoformat()
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM audit_logs WHERE timestamp < ?", (cutoff,))
        deleted_count = cursor.rowcount
        conn.commit()
    logger.info(f"Archived {deleted_count} audit logs older than {days_to_keep} days.")
    return deleted_count


def create_user(username, password_hash, role="VERIFIER", email=None):
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _connect() as conn:
            conn.execute(
                """INSERT INTO users
                   (username, email, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, email, password_hash, role, now),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_by_username(username):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def set_user_password(user_id, password_hash):
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, auth_version = auth_version + 1 WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()


def update_user_email_verified(user_id):
    with _connect() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
        conn.commit()


def update_user_totp(user_id, secret, recovery_codes):
    with _connect() as conn:
        conn.execute(
            """UPDATE users SET totp_secret = ?, totp_enabled = 1, recovery_codes = ?,
               auth_version = auth_version + 1 WHERE id = ?""",
            (secret, json.dumps(recovery_codes), user_id),
        )
        row = conn.execute("SELECT auth_version FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.commit()
        return row["auth_version"]


def consume_recovery_code(user_id, code_hash):
    with _connect() as conn:
        row = conn.execute("SELECT recovery_codes FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not row["recovery_codes"]:
            return False
        codes = json.loads(row["recovery_codes"])
        if code_hash not in codes:
            return False
        codes.remove(code_hash)
        conn.execute("UPDATE users SET recovery_codes = ? WHERE id = ?", (json.dumps(codes), user_id))
        conn.commit()
        return True


def create_auth_token(user_id, purpose, raw_token, expires_at):
    now = datetime.now(timezone.utc).isoformat()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with _connect() as conn:
        # Only the newest link for a given account and purpose is valid.
        conn.execute(
            """UPDATE auth_tokens SET used_at = ?
               WHERE user_id = ? AND purpose = ? AND used_at IS NULL""",
            (now, user_id, purpose),
        )
        conn.execute(
            """INSERT INTO auth_tokens
               (user_id, purpose, token_hash, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, purpose, token_hash, expires_at, now),
        )
        conn.commit()


def consume_auth_token(raw_token, purpose):
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        row = conn.execute(
            """SELECT id, user_id, expires_at, used_at FROM auth_tokens
               WHERE token_hash = ? AND purpose = ?""",
            (token_hash, purpose),
        ).fetchone()
        if not row or row["used_at"] or row["expires_at"] <= now:
            return None
        conn.execute("UPDATE auth_tokens SET used_at = ? WHERE id = ?", (now, row["id"]))
        conn.execute(
            """UPDATE auth_tokens SET used_at = ?
               WHERE user_id = (SELECT user_id FROM auth_tokens WHERE id = ?)
                 AND purpose = ? AND id != ? AND used_at IS NULL""",
            (now, row["id"], purpose, row["id"]),
        )
        conn.commit()
        return row["user_id"]

def create_user(username, password_hash, role="VERIFIER", email=None):
    now = datetime.now(timezone.utc).isoformat()
    try:
        with _connect() as conn:
            conn.execute(
                """INSERT INTO users
                   (username, email, password_hash, role, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (username, email, password_hash, role, now),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_by_username(username):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_user_by_email(email):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def set_user_password(user_id, password_hash):
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, auth_version = auth_version + 1 WHERE id = ?",
            (password_hash, user_id),
        )
        conn.commit()


def update_user_email_verified(user_id):
    with _connect() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user_id,))
        conn.commit()


def update_user_totp(user_id, secret, recovery_codes):
    with _connect() as conn:
        conn.execute(
            """UPDATE users SET totp_secret = ?, totp_enabled = 1, recovery_codes = ?,
               auth_version = auth_version + 1 WHERE id = ?""",
            (secret, json.dumps(recovery_codes), user_id),
        )
        row = conn.execute("SELECT auth_version FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.commit()
        return row["auth_version"]


def consume_recovery_code(user_id, code_hash):
    """Atomically consume one recovery code.

    The removal is written back with a compare-and-swap on the exact stored
    value, so two concurrent logins presenting the same code cannot both
    succeed: the loser's UPDATE matches no row and returns False.
    """
    with _connect() as conn:
        row = conn.execute("SELECT recovery_codes FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not row["recovery_codes"]:
            return False
        stored = row["recovery_codes"]
        try:
            codes = json.loads(stored)
        except (TypeError, ValueError):
            logger.warning("Recovery codes for user %s are unreadable; refusing to consume.", user_id)
            return False
        if not isinstance(codes, list) or code_hash not in codes:
            return False
        remaining = [code for code in codes if code != code_hash]
        cursor = conn.execute(
            "UPDATE users SET recovery_codes = ? WHERE id = ? AND recovery_codes = ?",
            (json.dumps(remaining), user_id, stored),
        )
        conn.commit()
        return cursor.rowcount == 1


def create_auth_token(user_id, purpose, raw_token, expires_at):
    now = datetime.now(timezone.utc).isoformat()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with _connect() as conn:
        # Only the newest link for a given account and purpose is valid.
        conn.execute(
            """UPDATE auth_tokens SET used_at = ?
               WHERE user_id = ? AND purpose = ? AND used_at IS NULL""",
            (now, user_id, purpose),
        )
        conn.execute(
            """INSERT INTO auth_tokens
               (user_id, purpose, token_hash, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, purpose, token_hash, expires_at, now),
        )
        conn.commit()


def consume_auth_token(raw_token, purpose):
    """Consume a single-use token exactly once.

    Only the SHA-256 hash of the token is ever stored, and the token is spent
    with one conditional UPDATE that requires the row to still be unused and
    unexpired. Because SQLite serialises writers, a token presented twice
    concurrently can only be spent by the first request; the second one sees a
    rowcount of 0 and gets None back.
    """
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            """UPDATE auth_tokens SET used_at = ?
               WHERE token_hash = ? AND purpose = ?
                 AND used_at IS NULL AND expires_at > ?""",
            (now, token_hash, purpose, now),
        )
        if cursor.rowcount != 1:
            conn.commit()
            return None
        row = conn.execute(
            "SELECT id, user_id FROM auth_tokens WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        # Any sibling token for the same account/purpose is now obsolete.
        conn.execute(
            """UPDATE auth_tokens SET used_at = ?
               WHERE user_id = ? AND purpose = ? AND id != ? AND used_at IS NULL""",
            (now, row["user_id"], purpose, row["id"]),
        )
        conn.commit()
        return row["user_id"]
