# 05 — API REFERENCE

## Overview

This document provides a complete reference for every HTTP endpoint in the Certificate Authentication System. All endpoints are defined in `app.py` and served by the Flask development server.

**Base URL (development):** `http://127.0.0.1:5000`

**Content Types:**
- Web UI endpoints: `text/html` (Jinja2 templates)
- API endpoints: `application/json`

---

## Endpoint Summary

| # | Method | URL | Purpose | Response Type |
|---|--------|-----|---------|---------------|
| 1 | GET | `/` | Home page | HTML |
| 2 | GET | `/issue` | Issue certificate form | HTML |
| 3 | POST | `/issue` | Process certificate issuance | HTML |
| 4 | GET | `/verify` | Verify certificate form | HTML |
| 5 | POST | `/verify` | Process certificate verification | HTML |
| 6 | POST | `/api/issue` | API: Issue certificate | JSON |
| 7 | POST | `/api/verify` | API: Verify certificate | JSON |

---

## Endpoint 1: `GET /` — Home Page

**Purpose:** Render the application home page with the modern SPA-style shell.

**File:** `app.py` line 808-810

**Handler Function:** `home()`

**Code:**
```python
@app.route("/")
def home():
    return render_template("index.html")
```

**Parameters:** None

**Validation:** None

**Files Involved:**
- `templates/index.html` — Renders the home page with Tailwind CSS assets
- `static/assets/index-B161kKw8.css` — Tailwind CSS v4 compiled stylesheet
- `static/assets/index-CRd-Min5.js` — Tailwind UI component JavaScript

**Internal Execution:**
1. Flask receives GET request at `/`
2. `render_template("index.html")` loads `templates/index.html`
3. Template includes `<div id="root"></div>` and loads Tailwind assets
4. Returns HTML string to browser

**Return Value:** `200 OK` — HTML page (string)

**Errors:** None (static page)

---

## Endpoint 2: `GET /issue` — Issue Certificate Form

**Purpose:** Render the certificate issuance form page.

**File:** `app.py` lines 813-839

**Handler Function:** `issue()`

**Code:**
```python
@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        # ... POST handling (see Endpoint 3) ...
    return render_template("index.html")  # line 839
```

**Parameters:** None

**Validation:** None

**Files Involved:**
- `templates/index.html` — **BUG:** Renders index.html instead of issue.html

**Anomaly (confirmed from code):** The GET handler returns `index.html` (the home page) instead of `issue.html` (the issue form). This is likely a bug:
```python
return render_template("index.html")  # Should be "issue.html"
```

**Return Value:** `200 OK` — HTML page (home page, not issue form)

**Errors:** None

---

## Endpoint 3: `POST /issue` — Process Certificate Issuance

**Purpose:** Accept a certificate file upload, extract text via OCR, parse structured fields, generate a SHA-256 hash, store the hash in the blockchain, and display the result.

**File:** `app.py` lines 813-838

**Handler Function:** `issue()`

**Code:**
```python
@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        file = request.files.get("certificate")
        if not file or not allowed_file(file.filename):
            return render_template("issue.html", error="Invalid file type.")

        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        text = perform_ocr(filepath)
        details = extract_details(text)
        cert_hash = generate_hash(details)
        status = add_certificate(cert_hash)

        return render_template(
            "result.html",
            status=status,
            name=details["name"],
            course=details["course"],
            date=details["date"],
            cert_id=details["cert_id"],
            hash=cert_hash,
        )
```

**Parameters (form-data):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `certificate` | File | Yes | Certificate file (PDF, PNG, JPG, JPEG, DOCX, DOC) |

**Validation:**

| Check | Method | Failure Response |
|-------|--------|-----------------|
| File exists | `if not file` | `issue.html` with `error="Invalid file type."` |
| File extension | `allowed_file()` | `issue.html` with `error="Invalid file type."` |
| Extension check | Extension in `ALLOWED_EXTENSIONS` | `issue.html` with `error="Invalid file type."` |

**Allowed Extensions:** `pdf`, `png`, `jpg`, `jpeg`, `doc`, `docx`

**Files Involved:**
- `app.py` (lines 813-838) — Route handler
- `templates/issue.html` — Error display template
- `templates/result.html` — Success display template
- `uploads/` — File storage directory
- `blockchain.txt` — Hash storage

**Internal Execution:**
1. Receive file from `request.files["certificate"]`
2. Validate file extension via `allowed_file()`
3. Sanitize filename via `secure_filename()`
4. Save file to `uploads/<filename>`
5. Run OCR via `perform_ocr(filepath)` → raw text
6. Extract fields via `extract_details(text)` → dict
7. Generate hash via `generate_hash(details)` → SHA-256 hex string
8. Store hash via `add_certificate(cert_hash)` → status string
9. Render `result.html` with status, name, course, date, cert_id, hash

**Pipeline Dependencies:**
```
issue() → allowed_file() → secure_filename() → perform_ocr()
    → extract_details() → generate_hash() → add_certificate() → render_template()
```

**Return Value:** `200 OK` — HTML page with issuance result

**Template Context Variables:**

| Variable | Source | Example |
|----------|--------|---------|
| `status` | `add_certificate()` return | `"ISSUED SUCCESSFULLY"` or `"ALREADY EXISTS"` |
| `name` | `details["name"]` | `"John Doe"` |
| `course` | `details["course"]` | `"Python 101"` |
| `date` | `details["date"]` | `"01/15/2024"` |
| `cert_id` | `details["cert_id"]` | `"CERT-2024-001"` |
| `hash` | `cert_hash` | `"a1b2c3d4..."` |

**Note:** `details["university"]` and `details["year"]` are extracted but NOT passed to the template.

**Error States:**

| Condition | HTTP Status | Response |
|-----------|-------------|----------|
| No file uploaded | 200 | Renders `issue.html` with error message |
| Invalid file type | 200 | Renders `issue.html` with error message |
| OCR failure (empty text) | 200 | All fields show "Unknown", hash is generated, certificate is stored |
| Duplicate hash | 200 | Renders `result.html` with status "ALREADY EXISTS" |
| File save failure | 500 | Exception propagated (not caught) |

---

## Endpoint 4: `GET /verify` — Verify Certificate Form

**Purpose:** Render the certificate verification form page.

**File:** `app.py` line 864

**Handler Function:** `verify()`

**Code:**
```python
@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        # ... POST handling (see Endpoint 5) ...
    return render_template("index.html")
```

**Parameters:** None

**Validation:** None

**Files Involved:**
- `templates/index.html` — **BUG:** Renders index.html instead of verify.html

**Anomaly (confirmed from code):** Same bug as `GET /issue` — returns `index.html` instead of `verify.html`:
```python
return render_template("index.html")  # Should be "verify.html"
```

**Return Value:** `200 OK` — HTML page (home page, not verify form)

**Errors:** None

---

## Endpoint 5: `POST /verify` — Process Certificate Verification

**Purpose:** Accept a certificate file upload, extract text via OCR, parse structured fields, generate a SHA-256 hash, look up the hash in the blockchain, and display the verification result.

**File:** `app.py` lines 843-864

**Handler Function:** `verify()`

**Code:**
```python
@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        file = request.files.get("certificate")
        if not file or not allowed_file(file.filename):
            return render_template("verify.html")
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        text = perform_ocr(filepath)
        details = extract_details(text)
        cert_hash = generate_hash(details)
        status = verify_certificate(cert_hash)
        return render_template(
            "result.html",
            status=status,
            name=details["name"],
            course=details["course"],
            date=details["date"],
            cert_id=details["cert_id"],
            hash=cert_hash,
        )
    return render_template("index.html")
```

**Parameters (form-data):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `certificate` | File | Yes | Certificate file (PDF, PNG, JPG, JPEG, DOCX, DOC) |

**Validation:**

| Check | Method | Failure Response |
|-------|--------|-----------------|
| File exists | `if not file` | Renders `verify.html` (no error message) |
| File extension | `allowed_file()` | Renders `verify.html` (no error message) |

**Anomaly (confirmed from code):** Unlike the issue endpoint, the verify endpoint does NOT pass an error message to the template when validation fails:
```python
# Issue endpoint (line 817):
return render_template("issue.html", error="Invalid file type.")

# Verify endpoint (line 847):
return render_template("verify.html")  # No error variable!
```

**Files Involved:**
- `app.py` (lines 843-864) — Route handler
- `templates/verify.html` — Error display template (no error message shown)
- `templates/result.html` — Success display template
- `uploads/` — File storage directory
- `blockchain.txt` — Hash storage

**Internal Execution:**
1. Receive file from `request.files["certificate"]`
2. Validate file extension via `allowed_file()`
3. Sanitize filename via `secure_filename()`
4. Save file to `uploads/<filename>`
5. Run OCR via `perform_ocr(filepath)` → raw text
6. Extract fields via `extract_details(text)` → dict
7. Generate hash via `generate_hash(details)` → SHA-256 hex string
8. Look up hash via `verify_certificate(cert_hash)` → "VERIFIED" or "FAKE"
9. Render `result.html` with status, name, course, date, cert_id, hash

**Return Value:** `200 OK` — HTML page with verification result

**Template Context Variables:**

| Variable | Source | Example |
|----------|--------|---------|
| `status` | `verify_certificate()` return | `"VERIFIED"` or `"FAKE"` |
| `name` | `details["name"]` | `"John Doe"` |
| `course` | `details["course"]` | `"Python 101"` |
| `date` | `details["date"]` | `"01/15/2024"` |
| `cert_id` | `details["cert_id"]` | `"CERT-2024-001"` |
| `hash` | `cert_hash` | `"a1b2c3d4..."` |

**Error States:**

| Condition | HTTP Status | Response |
|-----------|-------------|----------|
| No file uploaded | 200 | Renders `verify.html` (no error message) |
| Invalid file type | 200 | Renders `verify.html` (no error message) |
| OCR failure (empty text) | 200 | All fields show "Unknown", hash generated, lookup returns "FAKE" |
| Hash not found | 200 | Renders `result.html` with status "FAKE" |
| Hash found | 200 | Renders `result.html` with status "VERIFIED" |

---

## Endpoint 6: `POST /api/issue` — API Certificate Issuance

**Purpose:** JSON API endpoint for certificate issuance. Accepts a certificate file upload, processes it, stores the hash in the blockchain, and returns the extracted fields and status as JSON.

**File:** `app.py` lines 899-912

**Handler Function:** `api_issue()`

**Code:**
```python
@app.route("/api/issue", methods=["POST"])
def api_issue():
    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
    try:
        details, cert_hash = _process_upload(file)
        status = add_certificate(cert_hash)
        resp = _details_to_api(details, cert_hash)
        resp["status"] = status
        return jsonify(resp)
    except Exception as e:
        logger.error("api_issue error: %s", e)
        return jsonify({"error": str(e)}), 500
```

**Parameters (multipart/form-data):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `certificate` | File | Yes | Certificate file (PDF, PNG, JPG, JPEG, DOCX, DOC) |

**Validation:**

| Check | Method | Failure Response |
|-------|--------|-----------------|
| File exists | `if not file` | `400 {"error": "Invalid file type"}` |
| File extension | `allowed_file()` | `400 {"error": "Invalid file type"}` |
| Any exception | `try/except` | `500 {"error": "<exception message>"}` |

**Files Involved:**
- `app.py` (lines 899-912) — Route handler
- `app.py` (lines 870-878) — `_process_upload()` helper
- `app.py` (lines 881-896) — `_details_to_api()` helper
- `uploads/` — File storage directory
- `blockchain.txt` — Hash storage

**Internal Execution:**
1. Receive file from `request.files["certificate"]`
2. Validate file extension via `allowed_file()`
3. Call `_process_upload(file)`:
   a. Sanitize filename via `secure_filename()`
   b. Save file to `uploads/<filename>`
   c. Run OCR via `perform_ocr(filepath)` → raw text
   d. Extract fields via `extract_details(text)` → details dict
   e. Generate hash via `generate_hash(details)` → cert_hash
   f. Return `(details, cert_hash)`
4. Store hash via `add_certificate(cert_hash)` → status string
5. Format response via `_details_to_api(details, cert_hash)` → response dict
6. Add `status` to response dict
7. Return `jsonify(resp)` with HTTP 200

**Success Response (200 OK):**
```json
{
    "name": "John Doe",
    "course": "Python 101",
    "date": "01/15/2024",
    "cert_id": "CERT-2024-001",
    "university": "University of Technology",
    "hash": "a1b2c3d4e5f6...",
    "status": "ISSUED SUCCESSFULLY"
}
```

**Error Responses:**

| HTTP Status | Response Body | Condition |
|-------------|---------------|-----------|
| 400 | `{"error": "Invalid file type"}` | No file or invalid extension |
| 500 | `{"error": "<exception message>"}` | Any exception during processing |

**Response Field Details:**

| Field | Source | Type | Example | Notes |
|-------|--------|------|---------|-------|
| `name` | `details["name"]` | String | `"John Doe"` | Defaults to `"Unknown"` |
| `course` | `details["course"]` | String | `"Python 101"` | Defaults to `"Unknown"` |
| `date` | `details["date"]` | String | `"01/15/2024"` | Falls back to `year` if `"Unknown"` |
| `cert_id` | `details["cert_id"]` | String | `"CERT-2024-001"` | Synthetic: `"CERT-" + hash[:9].upper()` if `"Unknown"` |
| `university` | `details["university"]` | String | `"University of Technology"` | Defaults to `"Unknown"` |
| `hash` | `cert_hash` | String | `"a1b2..."` | 64-char SHA-256 hex |
| `status` | `add_certificate()` | String | `"ISSUED SUCCESSFULLY"` | Or `"ALREADY EXISTS"` |

---

## Endpoint 7: `POST /api/verify` — API Certificate Verification

**Purpose:** JSON API endpoint for certificate verification. Accepts a certificate file upload, processes it, looks up the hash in the blockchain, and returns the extracted fields and verification status as JSON.

**File:** `app.py` lines 915-928

**Handler Function:** `api_verify()`

**Code:**
```python
@app.route("/api/verify", methods=["POST"])
def api_verify():
    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
    try:
        details, cert_hash = _process_upload(file)
        status = verify_certificate(cert_hash)
        resp = _details_to_api(details, cert_hash)
        resp["status"] = status
        return jsonify(resp)
    except Exception as e:
        logger.error("api_verify error: %s", e)
        return jsonify({"error": str(e)}), 500
```

**Parameters (multipart/form-data):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `certificate` | File | Yes | Certificate file (PDF, PNG, JPG, JPEG, DOCX, DOC) |

**Validation:**

| Check | Method | Failure Response |
|-------|--------|-----------------|
| File exists | `if not file` | `400 {"error": "Invalid file type"}` |
| File extension | `allowed_file()` | `400 {"error": "Invalid file type"}` |
| Any exception | `try/except` | `500 {"error": "<exception message>"}` |

**Files Involved:**
- `app.py` (lines 915-928) — Route handler
- `app.py` (lines 870-878) — `_process_upload()` helper
- `app.py` (lines 881-896) — `_details_to_api()` helper
- `uploads/` — File storage directory
- `blockchain.txt` — Hash storage

**Internal Execution:**
1. Receive file from `request.files["certificate"]`
2. Validate file extension via `allowed_file()`
3. Call `_process_upload(file)`:
   a. Sanitize filename via `secure_filename()`
   b. Save file to `uploads/<filename>`
   c. Run OCR via `perform_ocr(filepath)` → raw text
   d. Extract fields via `extract_details(text)` → details dict
   e. Generate hash via `generate_hash(details)` → cert_hash
   f. Return `(details, cert_hash)`
4. Look up hash via `verify_certificate(cert_hash)` → "VERIFIED" or "FAKE"
5. Format response via `_details_to_api(details, cert_hash)` → response dict
6. Add `status` to response dict
7. Return `jsonify(resp)` with HTTP 200

**Success Response (200 OK):**
```json
{
    "name": "John Doe",
    "course": "Python 101",
    "date": "01/15/2024",
    "cert_id": "CERT-2024-001",
    "university": "University of Technology",
    "hash": "a1b2c3d4e5f6...",
    "status": "VERIFIED"
}
```

**Error Responses:**

| HTTP Status | Response Body | Condition |
|-------------|---------------|-----------|
| 400 | `{"error": "Invalid file type"}` | No file or invalid extension |
| 500 | `{"error": "<exception message>"}` | Any exception during processing |

**Response Field Details:**

| Field | Source | Type | Example | Notes |
|-------|--------|------|---------|-------|
| `name` | `details["name"]` | String | `"John Doe"` | Defaults to `"Unknown"` |
| `course` | `details["course"]` | String | `"Python 101"` | Defaults to `"Unknown"` |
| `date` | `details["date"]` | String | `"01/15/2024"` | Falls back to `year` if `"Unknown"` |
| `cert_id` | `details["cert_id"]` | String | `"CERT-2024-001"` | Synthetic: `"CERT-" + hash[:9].upper()` if `"Unknown"` |
| `university` | `details["university"]` | String | `"University of Technology"` | Defaults to `"Unknown"` |
| `hash` | `cert_hash` | String | `"a1b2..."` | 64-char SHA-256 hex |
| `status` | `verify_certificate()` | String | `"VERIFIED"` | Or `"FAKE"` |

---

## Shared Helper Functions

### `_process_upload(file)` (lines 870-878)

**Purpose:** Shared helper used by both API endpoints. Saves the uploaded file, runs OCR, extracts fields, and generates a hash.

**Code:**
```python
def _process_upload(file):
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    text = perform_ocr(filepath)
    details = extract_details(text)
    cert_hash = generate_hash(details)
    return details, cert_hash
```

**Returns:** `tuple(dict, str)` — `(details_dict, cert_hash_hex_string)`

**Used by:** `api_issue()`, `api_verify()`

### `_details_to_api(details, cert_hash)` (lines 881-896)

**Purpose:** Shared helper used by both API endpoints. Converts the internal details dictionary into a standardized API response format with fallbacks for missing fields.

**Code:**
```python
def _details_to_api(details, cert_hash):
    date_val = details.get("date", "Unknown")
    if date_val == "Unknown":
        date_val = details.get("year", "Unknown")
    cert_id = details.get("cert_id", "Unknown")
    if cert_id == "Unknown":
        cert_id = "CERT-" + cert_hash[:9].upper()
    return {
        "name": details.get("name", "Unknown"),
        "course": details.get("course", "Unknown"),
        "date": date_val,
        "cert_id": cert_id,
        "university": details.get("university", "Unknown"),
        "hash": cert_hash,
    }
```

**Returns:** `dict` — API response dictionary

**Used by:** `api_issue()`, `api_verify()`

---

## Blockchain Functions

### `load_hashes()` (lines 784-788)

**Purpose:** Load all certificate hashes from `blockchain.txt`.

```python
def load_hashes():
    if not os.path.exists(BLOCKCHAIN_FILE):
        return set()
    with open(BLOCKCHAIN_FILE, "r") as f:
        return set(f.read().splitlines())
```

**Returns:** `set` of hash strings (empty if file doesn't exist)

### `add_certificate(cert_hash)` (lines 791-797)

**Purpose:** Add a certificate hash to the blockchain if not a duplicate.

```python
def add_certificate(cert_hash):
    hashes = load_hashes()
    if cert_hash in hashes:
        return "ALREADY EXISTS"
    with open(BLOCKCHAIN_FILE, "a") as f:
        f.write(cert_hash + "\n")
    return "ISSUED SUCCESSFULLY"
```

**Returns:** `"ISSUED SUCCESSFULLY"` or `"ALREADY EXISTS"`

### `verify_certificate(cert_hash)` (lines 800-802)

**Purpose:** Check if a certificate hash exists in the blockchain.

```python
def verify_certificate(cert_hash):
    hashes = load_hashes()
    return "VERIFIED" if cert_hash in hashes else "FAKE"
```

**Returns:** `"VERIFIED"` or `"FAKE"`

---

## Cross-Reference: Endpoint → Pipeline

| Endpoint | Primary Pipeline | Pipeline Document Reference |
|----------|-----------------|---------------------------|
| `GET /` | Application Startup | Pipeline 1 |
| `POST /issue` | Certificate Issue | Pipeline 2 |
| `POST /verify` | Certificate Verification | Pipeline 3 |
| `POST /api/issue` | API Issue | Pipeline 4 |
| `POST /api/verify` | API Verify | Pipeline 5 |
| All OCR endpoints | OCR Dispatch | Pipeline 6 |
| All endpoints with file upload | OCR → Extraction → Hash → Blockchain | Pipelines 7-19 |

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference |
| [04_PIPELINES.md](04_PIPELINES.md) | Detailed pipeline documentation |