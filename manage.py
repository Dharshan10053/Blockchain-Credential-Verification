import os
import sys
import getpass
from werkzeug.security import generate_password_hash

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.db import init_db, create_user, get_user_by_username

def create_admin():
    print("=== Create Admin User ===")
    init_db()
    
    username = input("Enter admin username [admin]: ").strip()
    if not username:
        username = "admin"
        
    existing = get_user_by_username(username)
    if existing:
        print(f"Error: User '{username}' already exists.")
        return
        
    password = getpass.getpass("Enter strong password: ")
    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        return
        
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: Passwords do not match.")
        return
        
    # Securely hash password
    pwd_hash = generate_password_hash(password)
    
    if create_user(username, pwd_hash, role="ADMIN"):
        print(f"Success: Admin user '{username}' created successfully.")
    else:
        print("Error: Failed to create user. It may already exist.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create_admin":
        create_admin()
    else:
        print("Usage: python manage.py create_admin")
