"""Standalone end-to-end simulation using isolated temporary storage."""

import hashlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import db as db_module
from backend.database.db import (
    get_certificate_by_token,
    init_db,
    log_verification,
    upsert_certificate,
)
from backend.utils.blockchain import Blockchain
from backend.utils.qr_generator import generate_qr_base64
from backend.utils.report_generator import generate_report
from backend.utils.verification import issue_certificate


def run_simulation():
    print("--- Starting CertAuth Phase 2 E2E Simulation ---")
    original_db_path = db_module._DB_PATH
    try:
        with tempfile.TemporaryDirectory(prefix="certauth-e2e-") as temp_dir:
            db_module._DB_PATH = os.path.join(temp_dir, "certificates.db")
            blockchain = Blockchain(os.path.join(temp_dir, "blockchain.json"))
            init_db()

            cert_hash = hashlib.sha256(b"mock-certificate-for-e2e").hexdigest()
            details = {
                "certificate_id": "CERT-MOCK-999",
                "name": "Jane Doe",
                "course": "Advanced Blockchain Engineering",
                "issuing_authority": (
                    "Global University of Extremely Long Names That Might Break "
                    "Layouts If Not Carefully Managed By Truncation"
                ),
                "date": "May 2026",
                "confidence_score": 92.5,
            }

            print("\n--- Issuing the Certificate ---")
            status = issue_certificate(cert_hash, details, blockchain)
            print(f"Blockchain Issue Status: {status}")

            print("\n--- Upserting to the Database ---")
            token = upsert_certificate(cert_hash, details, action="ISSUE")
            print(f"Generated UUID Token: {token}")

            print("\n--- Generating QR Code ---")
            qr_data = generate_qr_base64(token, "https://certauth.network", is_token=True)
            print(f"QR Data length: {len(qr_data)} characters")

            print("\n--- Generating PDF Report ---")
            result = {
                "name": details["name"],
                "course": details["course"],
                "cert_id": details["certificate_id"],
                "issuing_authority": details["issuing_authority"],
                "date": details["date"],
                "confidence_score": details["confidence_score"],
                "hash": cert_hash,
                "token": token,
            }
            pdf_path = generate_report(result, "https://certauth.network")
            print(f"PDF saved to: {pdf_path}")

            print("\n--- Simulating Verification via Token ---")
            record = get_certificate_by_token(token)
            if record:
                print(f"Record found in DB via token: {record['cert_hash']}")
                block = blockchain.find_by_hash(record["cert_hash"])
                if block:
                    print("Blockchain Integrity Verified: VALID")
                    log_verification(
                        "TOKEN_VIEW",
                        record["cert_hash"],
                        "VALID",
                        "127.0.0.1",
                        "Python Test",
                        "Simulated view",
                    )
                else:
                    print("Blockchain Integrity Failed: TAMPERED")
                    log_verification(
                        "TOKEN_VIEW",
                        record["cert_hash"],
                        "FAKE",
                        "127.0.0.1",
                        "Python Test",
                        "Simulated view",
                    )
            else:
                print("Record NOT FOUND in DB.")

            print("\n--- Simulation Complete ---")
    finally:
        db_module._DB_PATH = original_db_path


if __name__ == "__main__":
    run_simulation()
