"""
SQLite persistence layer.
"""
from __future__ import annotations
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "certificates.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
