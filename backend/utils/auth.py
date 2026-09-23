from functools import wraps
from flask import session, request, jsonify, redirect, url_for
import os
from backend.database.db import get_user_by_username, get_user_by_api_key_hash, get_user_by_id
import hashlib
import secrets

def _is_legacy_admin() -> bool:
    """Deprecated compatibility fallback for legacy X-Admin-Key."""
    if os.environ.get("ENABLE_LEGACY_ADMIN_KEY", "false").lower() != "true":
        return False
    key = os.environ.get("ADMIN_API_KEY")
    req_key = request.headers.get("X-Admin-Key")
    return bool(key and req_key and secrets.compare_digest(req_key, key))

def get_current_user():
    """Get the current authenticated user context from either session or API key."""
    # 1. Check API Key
    api_key = request.headers.get("X-Api-Key")
    if api_key:
        key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
        user = get_user_by_api_key_hash(key_hash)
        if user:
            return user

    # 2. Check Legacy Admin Key (synthetic context)
    if _is_legacy_admin():
        return {"id": -1, "username": "legacy_admin", "role": "ADMIN", "is_active": 1}
        
    # 3. Check Session
    if "user_id" in session:
        user = get_user_by_id(session["user_id"])
        if user and user["is_active"]:
            return user
            
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            # If it's an API request or expects JSON, return 401
            if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                return jsonify({"error": "Authentication required"}), 401
            # Otherwise redirect to login
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def require_role(roles: list[str]):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                    return jsonify({"error": "Authentication required"}), 401
                return redirect(url_for('login', next=request.url))
                
            if user["role"] not in roles:
                if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                    return jsonify({"error": "Forbidden: Insufficient privileges"}), 403
                # Render a generic 403 if it's a browser page
                # Since we can't easily import _render_error_page from app, just return text or abort
                from flask import abort
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
