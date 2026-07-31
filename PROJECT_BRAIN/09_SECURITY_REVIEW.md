# 09 — SECURITY REVIEW

## Overview

This document analyzes the security posture of the Certificate Authentication System. It covers authentication, authorization, input validation, upload security, session handling, secrets management, cryptographic integrity, and other security-relevant aspects.

**Important:** This is a documentation-only analysis. No security fixes are implemented or proposed in this document. All findings are based on repository inspection.

---

## Security Assessment Summary

| Area | Rating | Findings |
|------|--------|----------|
| Authentication | ❌ None | No authentication mechanism exists |
| Authorization | ❌ None | No role-based access control |
| Upload Validation | ⚠️ Weak | Extension-only check, no content validation |
| Input Validation | ⚠️ Partial | Filename sanitized, but no size/type limits |
| Session Management | ❌ None | Flask sessions not configured |
| Secrets Management | ⚠️ Weak | Debug mode enabled in production |
| Hashing | ✅ Adequate | SHA-256 used for certificate hashing |
| Blockchain Integrity | ⚠️ Partial | app.py: no validation; blockchain.py: chain validation |
| CSRF Protection | ❌ None | No CSRF tokens on forms |
| XSS Protection | ⚠️ Partial | Jinja2 auto-escapes, but user data displayed |
| Logging | ⚠️ Partial | Debug logging enabled, but no audit trail |
| File Storage | ⚠️ Weak | No cleanup, no access control, unlimited uploads |
| API Security | ❌ None | No API keys, rate limiting, or request validation |

---

## 1. Authentication

**Rating: ❌ None**

**Finding (confirmed from code):** The application has no authentication mechanism.

**Evidence:**
- No `flask_login`, `flask_httpauth`, or `flask_jwt_extended` imports
- No user model or database table
- No login/logout routes
- No session-based authentication checks
- No API keys or tokens for API endpoints
- No `@login_required` decorators
- No password hashing or storage

**Impact:**
- Any user can issue certificates without authorization
- Certificate issuance is a privileged operation that should be restricted to administrators
- Currently, any user with access to the web interface can issue certificates
- No audit trail of who issued which certificate

---

## 2. Authorization

**Rating: ❌ None**

**Finding (confirmed from code):** The application has no authorization mechanism. There are no user roles, permissions, or access control lists.

**Impact:**
- No distinction between administrators and end users
- The verify endpoint should be public, but issue should be protected
- All users have equal access to all functionality

---

## 3. Upload Validation

**Rating: ⚠️ Weak**

### File Extension Check (app.py lines 37-44)

```python
def allowed_file(filename: str) -> bool:
    if not filename:
        return False
    filename = filename.strip()
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS
```

**Weaknesses:**
1. **Extension-only check**: Only validates the file extension, not the actual file content (magic bytes)
2. **No MIME type validation**: Does not check `Content-Type` header or file signature
3. **No size limit**: No `MAX_CONTENT_LENGTH` configured — allows unlimited uploads (DoS vector)
4. **Double extension bypass**: `file.pdf.exe` passes the extension check (checks last extension only)
5. **No virus scanning**: Uploaded files are not scanned for malware

**Attack vectors:**
- Upload a malicious executable with a `.pdf` extension
- Upload extremely large files to fill disk space
- Upload files with special characters in filename (mitigated by `secure_filename()`)

### `secure_filename()` Usage (app.py lines 820, 848)

```python
filename = secure_filename(file.filename)
```

**Mitigation:** `werkzeug.utils.secure_filename()` sanitizes filenames by:
- Removing path separators (`/`, `\`)
- Removing special characters
- Limiting to ASCII-safe characters

**This is good practice**, but does not address the content validation gap.

---

## 4. Input Validation

**Rating: ⚠️ Partial**

### Validated Inputs

| Input | Validation | Method | Location |
|-------|-----------|--------|----------|
| File extension | ✓ | `allowed_file()` | app.py lines 37-44 |
| Filename safety | ✓ | `secure_filename()` | app.py lines 820, 848 |
| Missing file | ✓ | `if not file` | app.py lines 816, 845 |
| Empty OCR text | ✓ | `text or ""` | app.py line 730 |

### Unvalidated Inputs

| Input | Validation | Risk |
|-------|-----------|------|
| File content | ❌ | Malicious file upload |
| File size | ❌ | DoS via disk exhaustion |
| OCR text | ❌ | Unexpected characters in extraction |
| API request body | ❌ | Malformed requests |
| Form field names | ❌ | Parameter pollution |

---

## 5. Session Management

**Rating: ❌ None**

**Finding (confirmed from code):** Flask sessions are not configured.

**Evidence:**
- No `app.secret_key` configured (Flask uses a default empty key)
- No session data is stored or retrieved
- No `flask.session` usage

**Impact:**
- Sessions are not cryptographically signed
- Session data is not trusted
- CSRF protection (which requires sessions) is not possible

---

## 6. Secrets Management

**Rating: ⚠️ Weak**

### Hardcoded Paths

| Path | Location | Risk |
|------|----------|------|
| `C:\poppler\Library\bin\poppler-25.12.0\Library\bin` | `app.py` line 256 | Hardcoded Windows path — not portable |
| `C:\Program Files\Tesseract-OCR\tesseract.exe` | `ocr_utils.py` line 5 | Hardcoded Tesseract path |

### Debug Mode

```python
app.run(debug=True)  # app.py line 935
```

**Finding:** `debug=True` is enabled which:
- Exposes the Flask debugger (Werkzeug debugger) with interactive code execution
- Shows detailed error pages with stack traces
- Enables auto-reload (allows code injection via file write)
- The debugger PIN (120-054-635 from log) is potentially guessable

**Impact:** An attacker with access to the server could execute arbitrary Python code through the debugger console.

---

## 7. Hashing and Cryptography

**Rating: ✅ Adequate**

### Certificate Hashing (app.py lines 771-781)

```python
def generate_hash(details):
    data_string = (
        (details.get("name") or "Unknown") + "|" +
        (details.get("course") or "Unknown") + "|" +
        (details.get("university") or "Unknown") + "|" +
        (details.get("date") or "Unknown") + "|" +
        (details.get("cert_id") or "Unknown")
    )
    cert_hash = hashlib.sha256(data_string.encode()).hexdigest()
    return cert_hash
```

**Strengths:**
- SHA-256 is a cryptographically secure hash function
- 64-character hex output (256 bits) — sufficient for collision resistance
- Consistent field ordering ensures deterministic hashing

**Weaknesses:**
- **No normalization**: Extra spaces, different casing, or different formatting produce different hashes
- This means the same certificate OCR'd differently will produce a different hash, causing verification to fail
- The `utils/cert_hash.py` version addresses this with normalization, but it's not used by routes

### Blockchain Block Hashing (blockchain.py lines 54-66)

```python
def _calculate_hash(self) -> str:
    block_string = (
        str(self.index)
        + str(self.timestamp)
        + json.dumps(self._data, sort_keys=True, separators=(",", ":"))
        + str(self.previous_hash)
    )
    return hashlib.sha256(block_string.encode()).hexdigest()
```

**Strengths:**
- Deterministic JSON serialization (`sort_keys=True`, fixed separators)
- Includes all block fields in hash calculation
- Links to previous block via `previous_hash`

---

## 8. Blockchain Integrity

**Rating: ⚠️ Partial**

### app.py Version (blockchain.txt)

**Finding:** The `app.py` blockchain implementation has **no integrity validation**:

```python
def load_hashes():
    if not os.path.exists(BLOCKCHAIN_FILE):
        return set()
    with open(BLOCKCHAIN_FILE, "r") as f:
        return set(f.read().splitlines())
```

**Weaknesses:**
- Plain text file — anyone with file system access can modify, add, or remove hashes
- No chain validation — hashes are loaded as an unordered set
- No linkage between hashes — they are independent entries
- Append-only in practice, but no protection against tampering

### blockchain.py Version

**Finding:** The `blockchain.py` version has chain validation:

```python
def validate_chain(self) -> bool:
    # Verify genesis block
    genesis = self.chain[0]
    if genesis.index != 0 or genesis.previous_hash != "0":
        return False
    if genesis.hash != genesis._calculate_hash():
        return False
    # Verify each subsequent block
    for i in range(1, len(self.chain)):
        block = self.chain[i]
        prev_block = self.chain[i - 1]
        if block.previous_hash != prev_block.hash:
            return False
        if block.hash != block._calculate_hash():
            return False
    return True
```

**Strengths:**
- Validates genesis block (index=0, previous_hash="0")
- Validates each block's hash integrity
- Validates `previous_hash` linkage between blocks
- Auto-repair on validation failure (reindex, relink, rehash)

**Weaknesses:**
- Still vulnerable to file system tampering (but tampering is detectable)
- No proof-of-work or proof-of-stake
- Centralized — single file storage
- No consensus mechanism

---

## 9. CSRF Protection

**Rating: ❌ None**

**Finding (confirmed from code):** The application has no CSRF (Cross-Site Request Forgery) protection.

**Evidence:**
- No `flask_wtf.csrf` or `flask_seasurf` imports
- No CSRF tokens in forms
- No `@csrf.exempt` decorators (because CSRF is not configured)
- Form submissions accept POST requests from any origin

**Attack Scenario:**
1. An attacker creates a malicious website with a form that POSTs to `http://127.0.0.1:5000/issue`
2. If the victim is authenticated (currently no auth, so anyone can access), the certificate is issued without the victim's knowledge

---

## 10. XSS Protection

**Rating: ⚠️ Partial**

### Jinja2 Auto-Escaping

**Finding:** Jinja2, Flask's template engine, automatically escapes HTML in template variables. This provides basic XSS protection.

```html
<!-- result.html -->
<p><strong>Name:</strong> {{ name }}</p>
<p><strong>Course:</strong> {{ course }}</p>
```

**However**, the `index.html` template uses a `<div id="root"></div>` pattern with external JavaScript:

```html
<script type="module" src="{{ url_for('static', filename='assets/index-CRd-Min5.js') }}"></script>
```

If the JavaScript in `index-CRd-Min5.js` renders user-supplied data without sanitization, it could introduce XSS vulnerabilities.

**Risk:** Low — Jinja2 auto-escaping handles most cases. The main risk is if the JavaScript bundle processes user data unsafely.

---

## 11. Logging and Audit

**Rating: ⚠️ Partial**

### Current Logging

```python
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
```

**Strengths:**
- DEBUG level provides detailed logging
- Timestamps included for all log entries

**Weaknesses:**
- No audit trail for certificate issuance or verification
- No logging of who issued a certificate (no authentication)
- No logging of IP addresses for requests
- No structured logging (JSON format)
- No log rotation configured
- Logs written to stdout only (not persisted to file by default)
- `extraction_system.log` captures some output but is not actively managed

---

## 12. File Storage Security

**Rating: ⚠️ Weak**

### Upload Directory

```python
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
```

**Weaknesses:**
- **No cleanup**: Uploaded files are never deleted
- **No access control**: Any uploaded file is accessible if the path is known
- **No size limit**: Files can be arbitrarily large
- **No file type enforcement**: Content is never validated
- **Overwrite risk**: Same filename overwrites existing file

---

## 13. API Security

**Rating: ❌ None**

### API Endpoints

```python
@app.route("/api/issue", methods=["POST"])
def api_issue():
    ...

@app.route("/api/verify", methods=["POST"])
def api_verify():
    ...
```

**Weaknesses:**
- **No API keys**: Anyone can call the API endpoints
- **No rate limiting**: Unlimited requests (DoS vector)
- **No request validation**: Malformed requests are only caught by generic `try/except`
- **No authentication**: Same as web routes
- **No HTTPS**: Plain HTTP in development
- **CORS not configured**: No `flask-cors` — browsers may block cross-origin requests

---

## 14. Code Injection Vulnerabilities

### Assessment

| Vector | Risk | Evidence |
|--------|------|----------|
| SQL Injection | ✅ None | No SQL database used |
| Command Injection | ⚠️ Low | `pytesseract.image_to_string()` uses shell for Tesseract calls |
| Path Traversal | ⚠️ Low | `secure_filename()` mitigates, but `os.path.join` is used |
| XXE | ✅ None | No XML parsing |
| Deserialization | ✅ None | `json.loads()` is safe (no arbitrary code execution) |

**Path Traversal Risk:**
```python
filepath = os.path.join(UPLOAD_FOLDER, filename)
```
`secure_filename()` removes path separators, so traversal is prevented. However, if `secure_filename()` is bypassed, `os.path.join` could be exploited.

---

## 15. Environment and Deployment Security

### Development Server

```python
app.run(debug=True)  # app.py line 935
```

**Finding:** The application is designed to run with Flask's development server in debug mode. This is **not suitable for production**.

**Issues:**
- Single-threaded by default
- No HTTPS
- Debugger exposes code execution
- No production-grade error handling
- No load balancing support

### Dependency Vulnerabilities

**Finding:** The `requirements.txt` file specifies minimum versions but no maximum versions:
```
Flask>=2.0
Pillow>=9.0
pytesseract>=0.3.10
pdf2image>=1.16
```

**Risk:** Dependencies may have known vulnerabilities. Pinning exact versions and using vulnerability scanning (`pip-audit`, `safety`) would be beneficial.

---

## 16. Security Checklist

| Security Control | Status | Priority |
|-----------------|--------|----------|
| Authentication | ❌ Missing | Critical |
| Authorization (RBAC) | ❌ Missing | High |
| CSRF Protection | ❌ Missing | High |
| Upload Size Limit | ❌ Missing | High |
| File Content Validation | ❌ Missing | High |
| Debug Mode Disabled | ❌ Not configured | High |
| API Authentication | ❌ Missing | High |
| Rate Limiting | ❌ Missing | Medium |
| Session Secret Key | ❌ Missing | Medium |
| HTTPS | ❌ Not configured | Medium |
| Audit Logging | ❌ Missing | Medium |
| Input Sanitization | ⚠️ Partial | Medium |
| CORS Configuration | ❌ Missing | Low |
| Log Rotation | ❌ Missing | Low |
| Dependency Scanning | ❌ Missing | Low |

---

## 17. Security Recommendations

**Critical Priority:**
1. Implement authentication (flask_login or similar)
2. Add role-based access control (admin vs. user)
3. Add CSRF protection to all forms
4. Set `MAX_CONTENT_LENGTH` for uploads
5. Validate file content using magic bytes
6. Disable debug mode in production
7. Add API key authentication for API endpoints

**High Priority:**
8. Set `app.secret_key` from environment variable
9. Add rate limiting to API endpoints
10. Implement audit logging for all certificate operations
11. Add file size and type validation
12. Use normalized hashing (from `utils/cert_hash.py`)
13. Configure CORS properly

**Medium Priority:**
14. Add file cleanup mechanism for uploads
15. Implement structured logging (JSON)
16. Add log rotation
17. Use environment variables for all configuration
18. Pin dependency versions

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference |
| [06_CONFIGURATION.md](06_CONFIGURATION.md) | Configuration details |
| [10_DESIGN_DECISIONS.md](10_DESIGN_DECISIONS.md) | Architectural decisions |