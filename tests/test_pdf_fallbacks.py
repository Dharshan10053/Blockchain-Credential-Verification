import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from backend.database.db import init_db, upsert_certificate

def test_fallbacks():
    init_db()
    
    # Test Case 1: Standard AI-Extracted Certificate
    mock_hash_1 = "hash_standard"
    details_1 = {
        "certificate_id": "CERT-1",
        "name": "Alice Standard",
        "course": "Introduction to Data Structures",
        "issuing_authority": "Tech University",
        "date": "2026-05-24"
    }
    upsert_certificate(mock_hash_1, details_1, action="ISSUE")
    
    # Test Case 2: Legacy Entry missing 'course' but having 'certificate_title'
    mock_hash_2 = "hash_legacy"
    details_2 = {
        "certificate_id": "CERT-2",
        "student_name": "Bob Legacy",
        "certificate_title": "Advanced Masterclass in Distributed Blockchain Consensus Algorithms and Systems Architecture",
        "issuer": "Global Institute",
        # date missing intentionally
    }
    upsert_certificate(mock_hash_2, details_2, action="ISSUE")
    
    # Test Case 3: Fuzzy OCR fallback
    mock_hash_3 = "hash_ocr"
    details_3 = {
        "id": "CERT-3",
        "candidate_name": "Charlie OCR",
        "course_name": "Fundamentals of AI",
        "institution": "OCR Academy",
        "issued_on": "May 2026"
    }
    upsert_certificate(mock_hash_3, details_3, action="ISSUE")
    
    hashes = [mock_hash_1, mock_hash_2, mock_hash_3]
    
    print("Testing /report endpoints for fallback correctness...")
    with app.test_client() as client:
        for h in hashes:
            print(f"\n--- Fetching PDF for {h} ---")
            response = client.get(f'/report/{h}')
            if response.status_code == 200:
                print(f"Success! PDF generated.")
            else:
                print(f"Failed! Status: {response.status_code}")

if __name__ == '__main__':
    test_fallbacks()
