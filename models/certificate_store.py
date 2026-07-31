import json
import os

DB_FILE = "db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)

def add_certificate(cert_id, hash_value):
    db = load_db()
    db[cert_id] = hash_value
    save_db(db)

def verify_certificate(cert_id, hash_value):
    db = load_db()

    if cert_id not in db:
        return False

    return db[cert_id] == hash_value