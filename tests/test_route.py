import os
import sys

# Setup paths to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from backend.database.db import init_db, upsert_certificate
from backend.utils.blockchain import Blockchain

def test_download_report():
    init_db()
    
    # Insert a dummy record
    mock_hash = "mockhash999"
    details = {
        "certificate_id": "CERT-APP-1",
        "student_name": "Test User",
        "certificate_title": "Data Science Masterclass",
        "institution": "Test University",
        # intentionally leave out date to test fallback
    }
    
    token = upsert_certificate(mock_hash, details, action="ISSUE")
    
    print("Testing /report endpoint...")
    with app.test_client() as client:
        response = client.get(f'/report/{mock_hash}')
        if response.status_code == 200:
            print("Successfully generated PDF via /report/<hash>!")
            print("Headers:", response.headers.get("Content-Disposition"))
        else:
            print(f"Failed! Status: {response.status_code}")
            print(response.data)

if __name__ == '__main__':
    test_download_report()
