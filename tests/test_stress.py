import os
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from backend.database.db import get_all_certificates, archive_old_logs

def worker_verify(client, results, idx):
    try:
        # We will hit the limit pretty quick (20 per min)
        response = client.post('/api/verify')
        results[idx] = response.status_code
    except Exception as e:
        results[idx] = str(e)

def run_stress_test():
    print("--- Starting Phase 3 E2E Stress Test ---")
    app.config['TESTING'] = True
    
    # Needs GEMINI_API_KEY to start but we can mock it here
    if not os.environ.get("GEMINI_API_KEY"):
        os.environ["GEMINI_API_KEY"] = "MOCK_KEY_FOR_TESTING"
        
    with app.test_client() as client:
        # 1. Test Rate Limiter
        print("Testing rate limiter on /api/verify...")
        threads = []
        results = {}
        for i in range(25):
            t = threading.Thread(target=worker_verify, args=(client, results, i))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Analyze results (some should be 400 because no file, some should be 429 because of limit)
        status_counts = {}
        for code in results.values():
            status_counts[code] = status_counts.get(code, 0) + 1
            
        print(f"Rate Limiter Status Distribution: {status_counts}")
        if 429 in status_counts:
            print("SUCCESS: Rate Limiter correctly blocked excess requests (429 Too Many Requests).")
        else:
            print("WARNING: Did not hit rate limit. (Maybe limit is higher?)")
            
        # 2. Test Export Route (Admin Disabled)
        print("\nTesting /api/export security...")
        os.environ["ENABLE_ADMIN_EXPORT"] = "false"
        resp = client.get('/api/export')
        print(f"Export without auth HTTP Status: {resp.status_code}")
        if resp.status_code == 403:
            print("SUCCESS: Export route securely locked down.")
            
        # 3. Test Archive Logs
        print("\nTesting Log Archival...")
        deleted = archive_old_logs(days_to_keep=30)
        print(f"SUCCESS: Log archival utility ran without errors. Deleted {deleted} rows.")

    print("\n--- Phase 3 Stress Test Complete ---")

if __name__ == "__main__":
    run_stress_test()
