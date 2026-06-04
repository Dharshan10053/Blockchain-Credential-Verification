import os
import sys

# Setup paths to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set FLASK_ENV to development for testing
os.environ["FLASK_ENV"] = "development"

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
        # 1. Without credentials -> 403 Forbidden
        response = client.get(f'/report/{mock_hash}')
        assert response.status_code == 403
        
        # 2. With valid token -> 200 OK
        response = client.get(f'/report/{mock_hash}?token={token}')
        assert response.status_code == 200
        assert "Content-Disposition" in response.headers
        
        # 3. With invalid token -> 403 Forbidden
        response = client.get(f'/report/{mock_hash}?token=invalid_token_123')
        assert response.status_code == 403
        
        # 4. With admin key -> 200 OK
        os.environ["ADMIN_API_KEY"] = "super-secret-admin-key"
        response = client.get(f'/report/{mock_hash}', headers={"X-Admin-Key": "super-secret-admin-key"})
        assert response.status_code == 200
        
        # 5. With incorrect admin key -> 403 Forbidden
        response = client.get(f'/report/{mock_hash}', headers={"X-Admin-Key": "wrong-key"})
        assert response.status_code == 403

if __name__ == '__main__':
    test_download_report()
