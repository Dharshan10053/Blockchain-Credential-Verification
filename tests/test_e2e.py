import os
import sys
import json
import uuid

# Setup paths to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.db import init_db, upsert_certificate, get_certificate_by_token, log_verification
from backend.utils.blockchain import Blockchain
from backend.utils.verification import classify_status, issue_certificate
from backend.utils.report_generator import generate_report
from backend.utils.qr_generator import generate_qr_base64

def run_simulation():
    print("--- Starting CertAuth Phase 2 E2E Simulation ---")
    
    # 1. Initialize DB and Blockchain
    init_db()
    blockchain = Blockchain("blockchain.json")
    
    # 2. Mock Details from an Extraction
    mock_hash = "mockhash1234567890abcdef"
    details = {
        "certificate_id": "CERT-MOCK-999",
        "name": "Jane Doe",
        "course": "Advanced Blockchain Engineering",
        "issuing_authority": "Global University of Extremely Long Names That Might Break Layouts If Not Carefully Managed By Truncation",
        "date": "May 2026",
        "confidence_score": 92.5
    }
    
    # 3. Issue the Certificate
    print("\n--- Issuing Certificate ---")
    status = issue_certificate(mock_hash, details, blockchain)
    print(f"Blockchain Issue Status: {status}")
    
    # 4. Upsert to DB and generate Token
    print("\n--- Upserting to Database ---")
    token = upsert_certificate(mock_hash, details, action="ISSUE")
    print(f"Generated UUID Token: {token}")
    
    # 5. Generate QR Code
    print("\n--- Generating QR Code ---")
    qr_data = generate_qr_base64(token, "https://certauth.network", is_token=True)
    print(f"QR Data length: {len(qr_data)} characters")
    
    # 6. Generate PDF Report
    print("\n--- Generating PDF Report ---")
    result = {
        "name": details["name"],
        "course": details["course"],
        "cert_id": details["certificate_id"],
        "issuing_authority": details["issuing_authority"],
        "date": details["date"],
        "confidence_score": details["confidence_score"],
        "hash": mock_hash,
        "token": token
    }
    pdf_path = generate_report(result, "https://certauth.network")
    print(f"PDF saved to: {pdf_path}")
    
    # 7. Simulate Verification via Token
    print("\n--- Simulating Verification ---")
    record = get_certificate_by_token(token)
    if record:
        print(f"Record found in DB via token: {record['cert_hash']}")
        block = blockchain.find_by_hash(record['cert_hash'])
        if block:
            print("Blockchain Integrity Verified: VALID")
            log_verification("TOKEN_VIEW", record['cert_hash'], "VALID", "127.0.0.1", "Python Test", "Simulated view")
        else:
            print("Blockchain Integrity Failed: TAMPERED")
            log_verification("TOKEN_VIEW", record['cert_hash'], "FAKE", "127.0.0.1", "Python Test", "Simulated view")
    else:
        print("Record NOT FOUND in DB.")
        
    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    run_simulation()
