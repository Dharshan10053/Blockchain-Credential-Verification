# 01 — ARCHITECTURE

## System Architecture Overview

The Certificate Authentication System (CertiChain) follows a **monolithic web application architecture** with a clear **layered internal structure**. The system is deployed as a single Flask Python process that handles HTTP requests, performs OCR processing, extracts certificate fields, manages a blockchain data structure, and serves a web-based UI.

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                                      │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │                           Flask Web Server                                     │    │
│  │                                                                                │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐   │    │
│  │  │  Web Routes       │  │   API Routes      │  │  Static File Serving      │   │    │
│  │  │  ┌──────────────┐ │  │  ┌──────────────┐ │  │  ┌──────────────────────┐ │   │    │
│  │  │  │ GET  /        │ │  │  │ POST /api/   │ │  │  │ /static/css/         │ │   │    │
│  │  │  │ GET/POST      │ │  │  │ issue        │ │  │  │ /static/js/          │ │   │    │
│  │  │  │   /issue      │ │  │  │ POST /api/   │ │  │  │ /static/assets/      │ │   │    │
│  │  │  │ GET/POST      │ │  │  │ verify       │ │  │  └──────────────────────┘ │   │    │
│  │  │  │   /verify     │ │  │  └──────────────┘ │  └────────────────────────────┘   │    │
│  │  │  └──────────────┘ │  └──────────────────┘                                     │    │
│  │  └──────────────────────────────────────────────────────────────────────────────┘    │
│  │                                                                                      │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │  │                        Jinja2 Template Engine                                 │    │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │    │
│  │  │  │base.html │  │index.html│  │issue.html│  │verify.html│  │result.html│     │    │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │    │
│  │  └──────────────────────────────────────────────────────────────────────────────┘    │
│  └──────────────────────────────────────────────────────────────────────────────────────┘
│                                              │
└──────────────────────────────────────────────┼────────────────────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATION LOGIC LAYER                                 │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │  OCR PIPELINE                                                                  │    │
│  │                                                                                │    │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐  ┌───────────────┐ │    │
│  │  │ perform_ocr() │─▶│ _ocr_pdf()      │─▶│ _preprocess_  │─▶│ _ocr_image_  │ │    │
│  │  │ (dispatcher)  │  │ _ocr_image_file()│  │ for_ocr()    │  │ cv()         │ │    │
│  │  │               │  │ _text_from_docx()│  │ (preprocess)  │  │ (Tesseract)  │ │    │
│  │  │               │  │ _text_from_doc() │  │               │  │              │ │    │
│  │  └──────────────┘  └──────────────────┘  └───────────────┘  └───────────────┘ │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │  FIELD EXTRACTION PIPELINE                                                      │    │
│  │                                                                                │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────────┐ │    │
│  │  │ extract_details() │  │ _extract_name()  │  │  Pattern Config (from       │ │    │
│  │  │ (orchestrator)    │  │ _extract_course()│  │   config/extraction_        │ │    │
│  │  │                   │  │ _extract_date()  │  │   patterns.py)              │ │    │
│  │  │                   │  │ _extract_cert_id()│  │                              │ │    │
│  │  │                   │  │ _extract_        │  │                              │ │    │
│  │  │                   │  │   university()   │  │                              │ │    │
│  │  │                   │  │ _extract_year()  │  │                              │ │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────────────┘ │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │  HASH GENERATION                                                               │    │
│  │                                                                                │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐  │    │
│  │  │  generate_hash(details) → SHA-256( name|course|university|date|cert_id ) │  │    │
│  │  └─────────────────────────────────────────────────────────────────────────┘  │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │  BLOCKCHAIN LAYER                                                               │    │
│  │                                                                                │    │
│  │  ┌────────────────┐  ┌──────────────┐  ┌────────────────┐  ┌────────────────┐ │    │
│  │  │ load_hashes()  │  │ add_         │  │ verify_        │  │ (blockchain.py │ │    │
│  │  │ (from file)    │  │ certificate()│  │ certificate()  │  │  Block,        │ │    │
│  │  │                │  │ (to file)    │  │ (lookup)       │  │  Blockchain    │ │    │
│  │  └────────────────┘  └──────────────┘  └────────────────┘  │  classes)      │ │    │
│  │                                                            └────────────────┘ │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│  └──────────────────────────────────────────────────────────────────────────────────────┘
│                                              │
└──────────────────────────────────────────────┼────────────────────────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                               │
│                                                                                      │
│  ┌──────────────────────────┐  ┌──────────────────────────┐                         │
│  │  Filesystem Storage       │  │  JSON File Storage        │                         │
│  │                          │  │                          │                         │
│  │  ┌────────────────────┐  │  │  ┌────────────────────┐  │                         │
│  │  │  uploads/           │  │  │  │  blockchain.json   │  │                         │
│  │  │  (uploaded certs)   │  │  │  │  (chain storage)   │  │                         │
│  │  └────────────────────┘  │  │  ├────────────────────┤  │                         │
│  │  ┌────────────────────┐  │  │  │  issue_certificate │  │                         │
│  │  │  test_images/       │  │  │  │  .json (legacy)   │  │                         │
│  │  │  (test fixtures)    │  │  │  ├────────────────────┤  │                         │
│  │  └────────────────────┘  │  │  │  db.json (legacy    │  │                         │
│  │                          │  │  │  KV store)          │  │                         │
│  │                          │  │  └────────────────────┘  │                         │
│  └──────────────────────────┘  └──────────────────────────┘                         │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐    │
│  │  External Dependencies                                                            │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │    │
│  │  │  Tesseract   │  │  Poppler     │  │  OpenCV      │  │  PyMuPDF (fitz)  │   │    │
│  │  │  OCR Engine  │  │  (pdf2image) │  │  (cv2)       │  │  (PDF parsing)   │   │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘   │    │
│  └──────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## Module Relationships

### Primary Module Dependency Graph (app.py)

```
app.py
├── flask (Flask, render_template, request, jsonify)
├── os
├── hashlib
├── logging
├── re
├── cv2 (OpenCV)
├── numpy as np
├── pytesseract
├── PIL (Pillow)
├── pdf2image
├── fitz (PyMuPDF)
└── werkzeug (secure_filename)
```

The `app.py` file is **self-contained** — it does NOT import from any of the refactored modules (`routes/`, `models/`, `utils/`, `config/`). It has its own implementations of OCR, field extraction, hash generation, and blockchain operations.

### Refactored Module Dependency Graph (not integrated into app.py)

```
routes/upload.py
├── flask (Blueprint, render_template, request)
└── werkzeug (secure_filename)

routes/verify.py
├── flask (Blueprint, render_template, request)
├── models.ocr (extract_text, extract_details)
├── models.hash_utils (generate_hash)
└── models.certificate_store (verify_certificate)

models/ocr.py
├── pytesseract
├── PIL (Pillow)
├── pdf2image
├── config.extraction_patterns (get_date_patterns, get_id_patterns, etc.)
└── re

models/hash_utils.py
├── hashlib
└── re

models/certificate_store.py
├── json
└── os

config/__init__.py
└── config.extraction_patterns (get_date_patterns, etc.)

config/extraction_patterns.py
└── typing (List, Dict, Any)

utils/cert_hash.py
├── hashlib
└── re

utils/__init__.py
└── utils.cert_hash (build_canonical_payload, generate_cert_hash)

blockchain.py
├── copy
├── hashlib
├── json
├── os
├── datetime
└── typing (List, Dict, Any, Optional)
```

## Startup Sequence

```
1. Python loads app.py
2.     ├── Import: flask, os, hashlib, logging, re, cv2, numpy, pytesseract, PIL, pdf2image, fitz, werkzeug
3.     ├── Configure logging.basicConfig(level=DEBUG)
4.     ├── Create Flask application instance: app = Flask(__name__)
5.     ├── Set constants: UPLOAD_FOLDER = "uploads", BLOCKCHAIN_FILE = "blockchain.txt"
6.     ├── Create uploads directory: os.makedirs(UPLOAD_FOLDER, exist_ok=True)
7.     ├── Set ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}
8.     ├── Define helper functions (allowed_file, _deskew, _preprocess_for_ocr, etc.)
9.     ├── Define OCR functions (perform_ocr, _ocr_pdf, _ocr_image_file, etc.)
10.    ├── Define field extraction functions (extract_details, _extract_name, etc.)
11.    ├── Define blockchain functions (generate_hash, load_hashes, add_certificate, verify_certificate)
12.    ├── Define route handlers (home, issue, verify, api_issue, api_verify)
13.    └── If __name__ == "__main__": app.run(debug=True)
14.         └── Flask development server starts on http://127.0.0.1:5000
```

## Request Lifecycle

### Certificate Issue Flow (Web UI)

```
1. User navigates to GET /issue
2.     → Flask returns issue.html template
3. User selects a certificate file and submits POST /issue
4.     → Flask receives request with file in request.files["certificate"]
5.     → allowed_file() validates file extension
6.     → secure_filename() sanitizes filename
7.     → File saved to uploads/<filename>
8.     → perform_ocr(filepath)
9.         ├── Dispatches to _ocr_pdf(), _ocr_image_file(), _text_from_docx(), or _text_from_doc()
10.        └── Returns raw OCR text
11.    → extract_details(text)
12.        ├── Splits text into lines
13.        ├── _extract_name(lines, full_text) → "name"
14.        ├── _extract_course(lines, full_text) → "course"
15.        ├── _extract_date(full_text) → "date"
16.        ├── _extract_cert_id(full_text) → "cert_id"
17.        ├── _extract_university(lines) → "university"
18.        ├── _extract_year(full_text) → "year"
19.        └── Returns dict with all fields
20.    → generate_hash(details) → SHA-256 hex digest
21.    → add_certificate(cert_hash) → "ISSUED SUCCESSFULLY" or "ALREADY EXISTS"
22.        ├── load_hashes() from blockchain.txt
23.        ├── Check if hash already exists
24.        └── Append hash to blockchain.txt
25.    → render_template("result.html", status, name, course, date, cert_id, hash)
26.    → Response returned to browser
```

### Certificate Verification Flow (Web UI)

```
1. User navigates to GET /verify
2.     → Flask returns verify.html template
3. User selects a certificate file and submits POST /verify
4.     → Flask receives request with file in request.files["certificate"]
5.     → allowed_file() validates file extension
6.     → secure_filename() sanitizes filename
7.     → File saved to uploads/<filename>
8.     → perform_ocr(filepath) → raw OCR text
9.     → extract_details(text) → dict with fields
10.    → generate_hash(details) → SHA-256 hex digest
11.    → verify_certificate(cert_hash) → "VERIFIED" or "FAKE"
12.        ├── load_hashes() from blockchain.txt
13.        └── Check if hash exists in loaded set
14.    → render_template("result.html", status, name, course, date, cert_id, hash)
15.    → Response returned to browser
```

### API Request Flow (JSON)

```
1. Client sends POST /api/issue or POST /api/verify
2.     → Flask receives request with file in request.files["certificate"]
3.     → allowed_file() validates file extension
4.     → _process_upload(file) helper
5.         ├── Saves file to uploads/
6.         ├── perform_ocr() → text
7.         ├── extract_details() → details dict
8.         ├── generate_hash() → cert_hash
9.         └── Returns (details, cert_hash)
10.    → add_certificate() or verify_certificate() for the status
11.    → _details_to_api() formats response dict
12.    → Returns jsonify(resp) with HTTP 200 or 400/500 on error
```

## Response Lifecycle

```
1. Route handler returns a response
2.     ├── For Web UI: render_template() returns HTML string
3.     │   ├── Jinja2 renders template with context variables
4.     │   └── HTML + CSS + JS sent to browser
5.     └── For API: jsonify() returns JSON response
6.         └── JSON payload with status, extracted fields, and hash
```

## Data Movement

### Certificate Issue (data flow)

```
File Upload ──▶ Filesystem (uploads/) ──▶ OCR Pipeline ──▶ Text ──▶ Extraction Pipeline ──▶ Fields Dict
                                                                                              │
                                                                                              ▼
                                                                                     Hash Generation
                                                                                              │
                                                                                              ▼
                                                                              ┌──────────────────────┐
                                                                              │  blockchain.txt      │
                                                                              │  (append hash)       │
                                                                              └──────────────────────┘
```

### Certificate Verification (data flow)

```
File Upload ──▶ Filesystem (uploads/) ──▶ OCR Pipeline ──▶ Text ──▶ Extraction Pipeline ──▶ Fields Dict
                                                                                              │
                                                                                              ▼
                                                                                     Hash Generation
                                                                                              │
                                                                                              ▼
                                                                              ┌──────────────────────┐
                                                                              │  blockchain.txt      │
                                                                              │  (hash lookup)       │
                                                                              │  → "VERIFIED"/"FAKE" │
                                                                              └──────────────────────┘
```

## Component Interaction Matrix

| Component | Depends On | Used By | Data Format |
|-----------|-----------|---------|-------------|
| Flask Routes | All components | Browser/API Client | HTTP Request/Response |
| allowed_file() | None | issue(), verify(), api_issue(), api_verify() | String → Boolean |
| perform_ocr() | _ocr_pdf(), _ocr_image_file(), _text_from_docx(), _text_from_doc() | issue(), verify(), _process_upload() | File path → String |
| _preprocess_for_ocr() | _deskew(), cv2, numpy | _ocr_image_cv(), _ocr_image_file() | ndarray → ndarray |
| _ocr_image_cv() | _preprocess_for_ocr(), pytesseract | _ocr_image_file() | ndarray → String |
| _ocr_pdf() | fitz, pdf2image, _preprocess_for_ocr(), pytesseract | perform_ocr() | File path → String |
| extract_details() | _extract_name(), _extract_course(), _extract_date(), _extract_cert_id(), _extract_university(), _extract_year() | issue(), verify(), _process_upload() | String → Dict |
| generate_hash() | hashlib | issue(), verify(), _process_upload() | Dict → String |
| load_hashes() | None (file I/O) | add_certificate(), verify_certificate() | None → Set |
| add_certificate() | load_hashes() | issue(), api_issue() | String → String |
| verify_certificate() | load_hashes() | verify(), api_verify() | String → String |
| _details_to_api() | None | api_issue(), api_verify() | Dict → Dict |

## Key Architectural Observations

### 1. Dual Codebase Architecture

The project contains **two parallel implementations**:

| Aspect | Primary (app.py) | Refactored (routes/, models/, utils/, config/) |
|--------|-----------------|------------------------------------------------|
| **Status** | Actively used by Flask routes | Separate Blueprint-based modules, NOT imported by app.py |
| **OCR** | Advanced preprocessing (deskew, denoise, multi-PSM, upscaling) | Basic (pytesseract.image_to_string only) |
| **Field Extraction** | Rich extraction with label/trigger/layout/regex strategies | Uses config/extraction_patterns.py (more configurable) |
| **Blockchain** | Simple text file (blockchain.txt) with hash set | Full Block/Blockchain class with JSON persistence (blockchain.json) |
| **Hashing** | Simple concatenation with pipe separators | Canonical normalization in utils/cert_hash.py |
| **Routes** | All routes in app.py | Separate Blueprint files |

### 2. Two Blockchain Implementations

| Feature | app.py (simple) | blockchain.py (full) |
|---------|----------------|---------------------|
| **Storage** | `blockchain.txt` (plain text, one hash per line) | `blockchain.json` (structured JSON with blocks) |
| **Block Structure** | None (just hash strings) | index, timestamp, data, previous_hash, hash |
| **Chain Validation** | None | validate_chain() on load |
| **Duplicate Detection** | Yes (set membership) | Via find_block_by_cert_hash() |
| **Legacy Migration** | None | Auto-migrate from issue_certificate.json |
| **Used By Routes** | **Yes** (app.py routes use this) | **No** (not imported by app.py) |

### 3. Two Hashing Approaches

| Feature | app.py generate_hash() | utils/cert_hash.py generate_cert_hash() |
|---------|----------------------|----------------------------------------|
| **Input Fields** | name, course, university, date, cert_id | name, course, date, cert_id |
| **Normalization** | None | Whitespace collapse, lowercase for non-name fields |
| **Separator** | Pipe (`\|`) | Pipe (`\|`) |
| **Used By Routes** | **Yes** | **No** |

### 4. Template Rendering Inconsistency

The `issue()` route renders `result.html` but the `issue()` GET handler returns `index.html` instead of `issue.html`:

```python
@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        # ... processing ...
        return render_template("result.html", ...)
    return render_template("index.html")  # ← Should be issue.html based on purpose
```

### 5. Error Handling Strategy

- **OCR Failures**: Return empty string, logged as warning
- **Extraction Failures**: Return "Unknown" or "Not Provided" for each field
- **Blockchain Corruption**: `blockchain.py` raises `BlockchainCorruptionError` with a descriptive message
- **API Errors**: Return JSON with `{"error": "..."}` and HTTP 400/500
- **Missing Uploads**: Return error message rendered in template
- **File Read Errors**: Logged, return empty string

## Execution Flow Diagrams

### OCR Pipeline Flow

```
                    ┌──────────────┐
                    │  File Upload │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ perform_ocr()│
                    │ (dispatcher) │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┬────────────┐
              ▼            ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ .pdf     │ │ .png/jpg │ │ .docx    │ │ .doc     │
        │          │ │ .jpeg    │ │          │ │          │
        └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
             │            │            │            │
             ▼            ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │_ocr_pdf()│ │_ocr_     │ │_text_    │ │_text_    │
        │          │ │image_    │ │from_     │ │from_     │
        │          │ │file()    │ │docx()    │ │doc()     │
        └────┬─────┘ └────┬─────┘ └──────────┘ └──────────┘
             │            │
             ▼            ▼
     ┌──────────────┐  ┌──────────────────┐
     │ PyMuPDF      │  │ cv2.imread()     │
     │ (digital     │  │                  │
     │  text)       │  │                  │
     └──────┬───────┘  └────────┬─────────┘
            │                   │
            ▼                   ▼
     ┌──────────────┐  ┌──────────────────┐
     │ ≥200 chars?  │  │ _preprocess_for_ │
     │              │  │ ocr()            │
     │ Yes → Return │  │                  │
     │ No  → OCR    │  │ 1. Upscale       │
     │ fallback     │  │ 2. Grayscale     │
     └──────────────┘  │ 3. GaussianBlur  │
            │          │ 4. Denoise (NL)  │
            ▼          │ 5. Deskew        │
     ┌──────────────┐  │ 6. Otsu binary   │
     │ pdf2image    │  └────────┬─────────┘
     │ (450 DPI)    │           │
     └──────┬───────┘           ▼
            │           ┌──────────────┐
            ▼           │ pytesseract  │
     ┌──────────────┐   │ (PSM 3,4,6) │
     │ _preprocess_ │   └──────────────┘
     │ for_ocr()    │           │
     └──────┬───────┘           ▼
            │           ┌──────────────┐
            ▼           │ Best result  │
     ┌──────────────┐   │ by length    │
     │ pytesseract  │   └──────────────┘
     │ (PSM 3,4,6)  │           │
     └──────┬───────┘           ▼
            │           ┌──────────────┐
            ▼           │  Return raw  │
     ┌──────────────┐   │  OCR text    │
     │ advanced_    │   └──────────────┘
     │ clean()      │
     └──────────────┘
            │
            ▼
     ┌──────────────┐
     │ Return text  │
     └──────────────┘
```

### Field Extraction Flow

```
                    ┌──────────────┐
                    │  Raw OCR     │
                    │  Text        │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Split into   │
                    │ lines &      │
                    │ full_text    │
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ Name         │  │ Course       │  │ Date         │
  │ Extraction   │  │ Extraction   │  │ Extraction   │
  │              │  │              │  │              │
  │ 1. Label     │  │ 1. Label     │  │ 1. Label     │
  │    match     │  │    match     │  │    match     │
  │ 2. Trigger   │  │ 2. Degree    │  │ 2. Regex     │
  │    phrase    │  │    pattern   │  │    patterns  │
  │ 3. Layout    │  │ 3. Trigger   │  │    (many     │
  │    (OCR      │  │    phrase    │  │    formats)  │
  │    coords)   │  │              │  │              │
  │ 4. Fallback  │  │              │  │              │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                 │
         ▼                 ▼                 ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ Cert ID      │  │ University   │  │ Year         │
  │ Extraction   │  │ Extraction   │  │ Extraction   │
  │              │  │              │  │              │
  │ 1. Label     │  │ 1. Keyword   │  │ 1. Regex     │
  │    match     │  │    scoring   │  │    (19xx,    │
  │ 2. Regex     │  │              │  │     20xx)    │
  │    patterns  │  │              │  │              │
  │ 3. URL       │  │              │  │              │
  │    patterns  │  │              │  │              │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Combined    │
                    │  Fields Dict │
                    │              │
                    │  name        │
                    │  course      │
                    │  university  │
                    │  year        │
                    │  date        │
                    │  cert_id     │
                    │  full_text   │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Hash Gen    │
                    └──────────────┘
```

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview, goals, technology stack |
| [02_DIRECTORY_STRUCTURE.md](02_DIRECTORY_STRUCTURE.md) | Directory tree and folder responsibilities |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference for all important files |
| [04_PIPELINES.md](04_PIPELINES.md) | Detailed pipeline documentation with sequence diagrams |
| [05_API_REFERENCE.md](05_API_REFERENCE.md) | Flask endpoint reference |
| [10_DESIGN_DECISIONS.md](10_DESIGN_DECISIONS.md) | Architectural decisions and rationale |