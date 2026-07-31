# 03 — FILE REFERENCE

This document provides a detailed reference for every important file in the repository. Each file entry includes its purpose, responsibilities, classes, functions, imports, dependencies, callers, callees, inputs, outputs, side effects, risk if modified, related files, and future improvement suggestions.

---

## `app.py` — Main Flask Application

**Purpose**: Primary application entry point. Contains Flask initialization, all web and API routes, OCR pipeline, field extraction, hash generation, and blockchain operations in a single monolithic file.

**File Path**: `c:\Projects\certificateproject\app.py`

**Lines**: 935

**Responsibilities**:
- Flask application initialization and configuration
- File upload handling and validation
- Image preprocessing pipeline (deskew, denoise, binarization)
- OCR text extraction (PDF, image, DOCX, DOC)
- Certificate field extraction (name, course, date, cert_id, university, year)
- Layout-based name detection using OCR coordinate data
- SHA-256 hash generation
- Simple text-based blockchain (blockchain.txt) management
- Web UI routes (GET /, GET/POST /issue, GET/POST /verify)
- JSON API endpoints (POST /api/issue, POST /api/verify)
- Logging configuration

**Imports**:
```python
from flask import Flask, render_template, request, jsonify
import os
import hashlib
import logging
import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
```

**Global Constants**:
| Constant | Value | Purpose |
|----------|-------|---------|
| `UPLOAD_FOLDER` | `"uploads"` | Directory for uploaded certificate files |
| `BLOCKCHAIN_FILE` | `"blockchain.txt"` | File for simple hash-based blockchain |
| `ALLOWED_EXTENSIONS` | `{"pdf", "png", "jpg", "jpeg", "doc", "docx"}` | Valid file extensions for upload |
| `NOT_PROVIDED` | `"Not Provided"` | Placeholder for missing field values |

**Functions**:

| Function | Lines | Purpose | Input | Output |
|----------|-------|---------|-------|--------|
| `allowed_file()` | 37-44 | Validate file extension against allowed set | `filename: str` | `bool` |
| `_deskew()` | 50-70 | Correct image skew angle using minAreaRect | `gray: np.ndarray` | `np.ndarray` |
| `_preprocess_for_ocr()` | 73-109 | Full preprocessing pipeline: upscale, grayscale, blur, denoise, deskew, binarize | `img_cv: np.ndarray` | `np.ndarray` |
| `_ocr_image_cv()` | 112-131 | Run Tesseract with multiple PSM configs, return best result | `img_cv: np.ndarray` | `str` |
| `_ocr_image_with_layout()` | 132-166 | OCR with layout information using image_to_data() | `img_cv: np.ndarray` | `list[dict]` |
| `_detect_name_from_layout()` | 167-200 | Detect name from OCR layout coordinates (largest centered text) | `blocks: list` | `str` |
| `_ocr_image_file()` | 206-214 | OCR for JPG/PNG/JPEG files | `file_path: str` | `str` |
| `_text_from_docx()` | 217-228 | Extract text from DOCX using python-docx | `file_path: str` | `str` |
| `_text_from_doc()` | 231-239 | Extract text from legacy .doc via textract | `file_path: str` | `str` |
| `_ocr_pdf()` | 242-366 | High-accuracy PDF text extraction (digital + OCR fallback + cleaning) | `file_path: str` | `str` |
| `perform_ocr()` | 369-391 | Route to appropriate extractor based on file extension | `filepath: str` | `str` |
| `_clean()` | 400-402 | Collapse whitespace and strip punctuation borders | `s: str` | `str` |
| `_valid()` | 405-413 | Return value if meaningful, else NOT_PROVIDED | `value: str` | `str` |
| `_label_extract()` | 416-437 | Search for 'Label: value' patterns across lines and full_text | `lines, full_text, labels, max_words` | `str` |
| `_extract_name()` | 443-507 | Extract recipient name using label, trigger, and fallback strategies | `lines, full_text` | `str` |
| `_extract_course()` | 510-563 | Extract course name using label, degree patterns, and triggers | `lines, full_text` | `str` |
| `_extract_date()` | 566-603 | Extract date using label patterns and regex | `full_text` | `str` |
| `_extract_cert_id()` | 606-652 | Extract certificate ID using labels, regex, and URL patterns | `full_text` | `str` |
| `_extract_university()` | 655-707 | Extract issuing organization using keyword scoring | `lines` | `str` |
| `_extract_year()` | 709-716 | Extract year using regex | `full_text` | `str` |
| `extract_details()` | 722-765 | Orchestrate all field extraction, return combined dict | `text: str` | `dict` |
| `generate_hash()` | 771-781 | Generate SHA-256 hash from certificate details | `details: dict` | `str` |
| `load_hashes()` | 784-788 | Load all hashes from blockchain.txt | None | `set` |
| `add_certificate()` | 791-797 | Add hash to blockchain.txt if not duplicate | `cert_hash: str` | `str` |
| `verify_certificate()` | 800-802 | Check if hash exists in blockchain | `cert_hash: str` | `str` |
| `_process_upload()` | 870-878 | Save file, run OCR, extract details, generate hash | `file` | `tuple(dict, str)` |
| `_details_to_api()` | 881-896 | Convert details dict to API response format | `details, cert_hash` | `dict` |

**Route Handlers**:

| Route | Method | Function | Purpose |
|-------|--------|----------|---------|
| `/` | GET | `home()` | Render index.html |
| `/issue` | GET, POST | `issue()` | Issue certificate (upload → OCR → extract → hash → store) |
| `/verify` | GET, POST | `verify()` | Verify certificate (upload → OCR → extract → hash → lookup) |
| `/api/issue` | POST | `api_issue()` | JSON API for certificate issuance |
| `/api/verify` | POST | `api_verify()` | JSON API for certificate verification |

**Dependencies**: Flask, OpenCV, numpy, pytesseract, Pillow, pdf2image, PyMuPDF, werkzeug

**Called by**: Executed directly (`python app.py`)

**Calls**: No internal modules (self-contained). Calls external libraries (cv2, pytesseract, etc.)

**Side Effects**:
- Creates `uploads/` directory on startup
- Writes uploaded files to `uploads/`
- Reads and writes `blockchain.txt`
- Logs debug information to console

**Risk if modified**: HIGH. This is the primary application file. Any changes affect all routes, OCR processing, extraction, and blockchain operations. Breaking changes here disable the entire application.

**Related files**: `app_backup.py` (earlier version), `templates/` (all templates rendered by this file), `blockchain.txt` (blockchain storage)

**Future improvements**:
- Split into separate modules (routes, OCR, extraction, blockchain)
- Register refactored Blueprints
- Use `blockchain.py` instead of `blockchain.txt`
- Use `config/extraction_patterns.py` for extraction patterns
- Fix GET /issue to render `issue.html` instead of `index.html`
- Add file type validation beyond extension check
- Add upload size limits
- Add database integration

---

## `app_backup.py` — Backup of Earlier Application Version

**Purpose**: Backup copy of an earlier version of `app.py`. Contains a simpler implementation with basic image preprocessing, OCR, field extraction, and the same routes.

**File Path**: `c:\Projects\certificateproject\app_backup.py`

**Lines**: 267

**Key Differences from app.py**:
- Simpler image preprocessing (`preprocess_image()`: grayscale, contrast, Gaussian blur, adaptive threshold)
- No deskew, no denoising, no upscaling
- Simpler OCR (single PSM mode, no multi-PSM selection)
- Simpler field extraction (basic regex, hardcoded keywords)
- Uses `generate_hash_from_file()` for issue route (file-based hash, not text-based)
- More limited file types: `{"png", "jpg", "jpeg", "pdf"}` (no DOC/DOCX)
- GET /issue renders `issue.html` (correct behavior)

**Status**: **Not used by current application**. Retained as a reference/backup.

---

## `blockchain.py` — Full Blockchain Implementation

**Purpose**: Complete blockchain implementation with `Block` and `Blockchain` classes. Provides chain validation, block structure, JSON persistence, legacy migration, and certificate hash lookup.

**File Path**: `c:\Projects\certificateproject\blockchain.py`

**Lines**: 250

**Responsibilities**:
- Define `Block` data structure with index, timestamp, data, previous_hash, hash
- Define `Blockchain` class with chain management
- Load chain from `blockchain.json` on initialization
- Save chain to `blockchain.json` after each modification
- Validate chain integrity (genesis block, hash links, previous_hash links)
- Auto-migrate from legacy `issue_certificate.json` format
- Prevent duplicate certificate hashes
- Find blocks by certificate hash

**Classes**:

### `Block`
| Attribute | Type | Description |
|-----------|------|-------------|
| `index` | `int` | Position in chain (0 = genesis) |
| `timestamp` | `str` | ISO 8601 timestamp with 'Z' suffix |
| `_data` | `Any` | Certificate payload (deep-copied dict) |
| `previous_hash` | `str` | Hash of previous block |
| `hash` | `str` | SHA-256 hash of this block |

| Method | Purpose |
|--------|---------|
| `__init__()` | Initialize block, auto-calculate hash if not provided |
| `data` (property) | Return deep-copied data |
| `_calculate_hash()` | SHA-256 of index + timestamp + JSON(data) + previous_hash |
| `to_dict()` | Serialize block to dictionary |
| `from_dict()` | Deserialize block from dictionary (classmethod) |

### `BlockchainCorruptionError`
Custom exception raised when `blockchain.json` is corrupted or invalid.

### `Blockchain`
| Attribute | Type | Description |
|-----------|------|-------------|
| `_path` | `str` | Path to blockchain.json |
| `chain` | `List[Block]` | In-memory chain of blocks |

| Method | Purpose |
|--------|---------|
| `__init__()` | Load or create chain, validate on startup |
| `_load_or_create()` | Load from file, migrate legacy, or create genesis |
| `_load_legacy()` | Load from issue_certificate.json, deduplicate by hash |
| `save_chain_to_path()` | Write chain to JSON file (static method) |
| `_create_genesis_block()` | Create genesis block (index=0, data="Genesis Block") |
| `_load_chain()` | Load chain from JSON file |
| `save()` | Persist chain to blockchain.json |
| `validate_chain()` | Verify genesis, hash links, previous_hash links |
| `get_last_block()` | Return last block in chain |
| `add_block()` | Create and append new block, save chain |
| `find_block_by_cert_hash()` | Find first block with matching certificate hash |

**Imports**: `copy`, `hashlib`, `json`, `os`, `datetime`, `typing`

**Dependencies**: Standard library only (no external dependencies)

**Called by**: `test_ocr.py`

**Not called by**: `app.py` (app.py uses its own simple blockchain implementation)

**Side Effects**:
- Creates `blockchain.json` on first run
- Modifies `blockchain.json` on each `add_block()`
- Reads `issue_certificate.json` for migration (if `blockchain.json` doesn't exist)

**Risk if modified**: MODERATE. This is a standalone module not used by the main application. However, if it's integrated in the future, breaking changes could affect chain integrity and validation.

**Related files**: `blockchain.json` (persistence), `issue_certificate.json` (legacy migration)

**Future improvements**:
- Integrate with `app.py` routes (replace `blockchain.txt` usage)
- Add block timestamp validation
- Add chain repair functionality
- Add proof-of-work or proof-of-stake mechanisms
- Add distributed consensus
- Add Merkle tree for efficient verification

---

## `blockchain.json` — Persisted Blockchain Data

**Purpose**: JSON file containing the persisted blockchain chain. Auto-generated by `blockchain.py`.

**File Path**: `c:\Projects\certificateproject\blockchain.json`

**Lines**: 25

**Current Content**:
```json
{
  "chain": [
    {
      "index": 0,
      "timestamp": "2026-03-03T12:12:52.018845Z",
      "data": "Genesis Block",
      "previous_hash": "0",
      "hash": "799b01503060bf5014efd9195747ff556a4a7adf6ec5767dfb6f269f2059bc00"
    },
    {
      "index": 1,
      "timestamp": "2026-03-03T12:18:29.780535Z",
      "data": {
        "certificate_id": "Int15762022233437",
        "name": "Jayanth",
        "course": "Intro To Python",
        "date": "10/18/2022",
        "hash": "22195dd9ba91859e7e119c68d16463b99731089457de252420ce24dd7ff28f8d"
      },
      "previous_hash": "799b01503060bf5014efd9195747ff556a4a7adf6ec5767dfb6f269f2059bc00",
      "hash": "512834999b66b6568a83805c2308262ca95bf0221d1e014bfb27f1683f49a3dd"
    }
  ],
  "updated_at": "2026-03-03T12:29:47.276326Z"
}
```

**Structure**: Contains a `chain` array of block objects and an `updated_at` timestamp.

**Blocks**: 2 blocks (1 genesis + 1 certificate)

**Status**: Contains 1 real certificate: "Jayanth" — "Intro To Python"

---

## `blockchain.txt` — Simple Text-Based Blockchain

**Purpose**: Plain text file containing one SHA-256 hash per line. Used by `app.py` routes as a simple blockchain.

**File Path**: `c:\Projects\certificateproject\blockchain.txt`

**Current Content**: (Empty or not present — file is created on first certificate issuance)

**Status**: Used by `app.py` routes. Each line represents a certificate hash.

---

## `issue_certificate.json` — Legacy Certificate Storage

**Purpose**: Legacy certificate storage from an earlier version of the application. Contains a flat list of certificate records with raw data and blockchain structure.

**File Path**: `c:\Projects\certificateproject\issue_certificate.json`

**Lines**: 42

**Current Content**: 4 legacy certificate records:
1. Index 1: "Jayanth" — "Python Modules" — hash: `1e9a0444...`
2. Index 2: "Jayanth" — "Script Introduction" — hash: `d60da89a...`
3. Index 3: "Unknown" — "Unknown" — hash: `dcf7785c...` (failed extraction)
4. Index 4: "KADARI JAYANTH" — "Unknown" — hash: `0412f4ab...`

**Status**: Legacy format. Automatically migrated to `blockchain.json` by `blockchain.py` if the new format doesn't exist.

---

## `ocr_utils.py` — Simple OCR Utility

**Purpose**: Standalone utility for basic OCR text extraction. Sets Tesseract path and provides a simple wrapper function.

**File Path**: `c:\Projects\certificateproject\ocr_utils.py`

**Lines**: 11

**Functions**:

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `extract_text()` | Extract text from image using PIL + pytesseract | `image_path: str` | `str` |

**Imports**: `pytesseract`, `PIL.Image`

**Notable**: Hardcodes Tesseract path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

**Status**: Not integrated into the main application. Simple reference implementation.

---

## `config/__init__.py` — Configuration Package Init

**Purpose**: Package initializer for the config module. Re-exports pattern functions from `extraction_patterns.py`.

**File Path**: `c:\Projects\certificateproject\config\__init__.py`

**Lines**: 15

**Exports**: `get_date_patterns()`, `get_id_patterns()`, `get_name_patterns()`, `get_course_patterns()`

**Used by**: `models/ocr.py`

---

## `config/extraction_patterns.py` — Extraction Pattern Configuration

**Purpose**: Centralized pattern definitions for certificate field extraction. All patterns are configurable lists, enabling support for different certificate layouts without code changes.

**File Path**: `c:\Projects\certificateproject\config\extraction_patterns.py`

**Lines**: 187

**Responsibilities**:
- Define date regex patterns (5 formats: slash, dash, month-name, day-month, ordinal)
- Define certificate ID patterns (regex + label keywords)
- Define name trigger phrases, label keywords, and fallback exclusion words
- Define course trigger phrases, label keywords, validation rules, and exclusion keywords

**Pattern Groups**:

### Date Patterns (`DATE_PATTERNS`)
5 regex patterns covering:
- `MM/DD/YYYY` or `MM-DD-YYYY` or `MM.DD.YYYY`
- `YYYY/MM/DD` or `YYYY-MM-DD` or `YYYY.MM.DD`
- `Month DD, YYYY` (e.g., "March 4, 2026")
- `DD Month YYYY` (e.g., "4 March 2026")
- `DDth Month YYYY` (e.g., "4th March 2026")

### ID Patterns (`ID_REGEX_PATTERNS`, `ID_LABEL_KEYWORDS`)
4 regex patterns and 6 label keywords for certificate ID extraction.

### Name Patterns (`NAME_TRIGGER_PHRASES`, `NAME_LABEL_KEYWORDS`, `NAME_FALLBACK_EXCLUDE`)
8 trigger phrases, 5 label keywords, 12 fallback exclusion words, and configuration constants.

### Course Patterns (`COURSE_TRIGGER_PHRASES`, `COURSE_LABEL_KEYWORDS`, `COURSE_EXCLUDE_KEYWORDS`)
9 trigger phrases, 5 label keywords, 7 exclusion keywords, and validation constants (max words, uppercase ratio, max commas, etc.).

**Functions**:

| Function | Returns |
|----------|---------|
| `get_date_patterns()` | `List[str]` — date regex patterns |
| `get_id_patterns()` | `Dict` — regex patterns + label keywords |
| `get_name_patterns()` | `Dict` — trigger phrases, labels, fallback config |
| `get_course_patterns()` | `Dict` — trigger phrases, labels, validation config |

**Used by**: `models/ocr.py`

**Not used by**: `app.py` (has its own hardcoded extraction logic)

**Risk if modified**: MODERATE. Changes to patterns affect extraction accuracy for all certificates. Adding patterns is safe; removing patterns may break extraction for certain layouts.

---

## `models/__init__.py` — Models Package Init

**Purpose**: Package initializer for the models module.

**File Path**: `c:\Projects\certificateproject\models\__init__.py`

**Lines**: 0 (empty file)

---

## `models/ocr.py` — OCR and Extraction Module

**Purpose**: Refactored OCR and pattern-based extraction module. Provides text extraction from images/PDFs and structured field extraction using configurable patterns from `config/extraction_patterns.py`.

**File Path**: `c:\Projects\certificateproject\models\ocr.py`

**Lines**: 240

**Responsibilities**:
- Text extraction from images and PDFs using Tesseract
- Pattern-based field extraction (name, course, date, cert_id)
- Text normalization and cleaning
- Integration with `config/extraction_patterns.py` for all patterns

**Functions**:

| Function | Purpose | Lines |
|----------|---------|-------|
| `_normalize_text()` | Normalize OCR text: collapse newlines, strip lines | 26-31 |
| `_extract_by_regex()` | Try each regex pattern, return first match | 34-42 |
| `_extract_date()` | Extract date using patterns from config | 45-51 |
| `_extract_cert_id()` | Extract cert ID using regex + label patterns | 54-66 |
| `_extract_name()` | Extract name using trigger phrases, labels, fallback | 69-110 |
| `_strip_invisible()` | Remove control characters, normalize whitespace | 113-116 |
| `_is_valid_course_line()` | Validate course candidate against config rules | 119-155 |
| `_extract_course()` | Extract course using triggers, labels, validation | 158-187 |
| `extract_details()` | Orchestrate all field extraction, return tuple | 190-209 |
| `extract_text()` | Extract text from image/PDF using Tesseract | 212-240 |

**Imports**: `re`, `pytesseract`, `PIL.Image`, `config.extraction_patterns`, `pdf2image`

**Dependencies**: `config/`, `pytesseract`, `PIL`, `pdf2image`

**Used by**: `routes/verify.py`, `test_ocr.py`

**Not used by**: `app.py` (has its own OCR implementation)

**Return format**: `extract_details()` returns a tuple `(name, course, date, cert_id, full_text)` — all strings. Unlike `app.py`'s version which returns a dict.

**Risk if modified**: MODERATE. Affects `routes/verify.py` and `test_ocr.py`. Breaking changes to function signatures or return values will break these consumers.

---

## `models/hash_utils.py` — Simple Hash Utility

**Purpose**: Simple utility for text normalization and SHA-256 hashing.

**File Path**: `c:\Projects\certificateproject\models\hash_utils.py`

**Lines**: 12

**Functions**:

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `normalize_text()` | Lowercase, collapse whitespace, remove non-alphanumeric | `text: str` | `str` |
| `generate_hash()` | SHA-256 hash of normalized text | `text: str` | `str` |

**Note**: The normalization is aggressive — it removes all non-alphanumeric characters including spaces (after collapsing). This may cause different OCR results to hash differently.

**Used by**: `routes/verify.py`

---

## `models/certificate_store.py` — JSON KV Certificate Store

**Purpose**: Simple JSON-based key-value store for certificate verification. Maps certificate IDs to hash values.

**File Path**: `c:\Projects\certificateproject\models\certificate_store.py`

**Lines**: 27

**Functions**:

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `load_db()` | Load database from `db.json` | None | `dict` |
| `save_db()` | Save database to `db.json` | `db: dict` | None |
| `add_certificate()` | Add certificate ID → hash mapping | `cert_id, hash_value` | None |
| `verify_certificate()` | Check if cert_id has matching hash | `cert_id, hash_value` | `bool` |

**Storage**: `db.json` (local file)

**Used by**: `routes/verify.py`

---

## `routes/upload.py` — Upload Blueprint

**Purpose**: Flask Blueprint for certificate upload handling.

**File Path**: `c:\Projects\certificateproject\routes\upload.py`

**Lines**: 24

**Routes**:

| Route | Method | Function | Purpose |
|-------|--------|----------|---------|
| `/` | GET | `index()` | Render `upload.html` |
| `/upload` | POST | `upload_certificate()` | Save uploaded file, render `verify.html` |

**Blueprint Name**: `upload`

**Imports**: `flask.Blueprint`, `flask.render_template`, `flask.request`, `werkzeug.secure_filename`, `os`

**Notable**: Saves files to `uploads/certificates/` subdirectory (different from `app.py`'s `uploads/`).

**Status**: **Not registered with the Flask app**. Inactive.

---

## `routes/verify.py` — Verify Blueprint

**Purpose**: Flask Blueprint for certificate verification using the refactored model modules.

**File Path**: `c:\Projects\certificateproject\routes\verify.py`

**Lines**: 35

**Routes**:

| Route | Method | Function | Purpose |
|-------|--------|----------|---------|
| `/` | POST | `verify_certificate_route()` | Verify certificate by filepath, render result |

**Blueprint Name**: `verify`

**Imports**: `flask.Blueprint`, `flask.render_template`, `flask.request`, `models.ocr`, `models.hash_utils`, `models.certificate_store`, `os`

**Execution Flow**:
1. Receive `filepath` from form data
2. Run OCR: `extract_text(filepath)`
3. Extract fields: `extract_details(raw_text)` → returns tuple
4. Build structured string: `f"{name}|{course}|{date}|{cert_id}"`
5. Generate hash: `generate_hash(structured)`
6. Verify: `verify_certificate(cert_id, hash_value)`
7. Render `result.html` with structured text, hash, and status

**Status**: **Not registered with the Flask app**. Inactive.

---

## `utils/__init__.py` — Utils Package Init

**Purpose**: Package initializer for the utils module. Re-exports canonical hash functions.

**File Path**: `c:\Projects\certificateproject\utils\__init__.py`

**Lines**: 5

**Exports**: `build_canonical_payload()`, `generate_cert_hash()`

---

## `utils/cert_hash.py` — Canonical Hash Utility

**Purpose**: Provides canonical certificate representation and deterministic hashing. Normalizes field values so minor OCR differences produce the same hash.

**File Path**: `c:\Projects\certificateproject\utils\cert_hash.py`

**Lines**: 48

**Functions**:

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `_normalize_field()` | Collapse whitespace, optionally lowercase | `value: str, preserve_case: bool` | `str` |
| `build_canonical_payload()` | Build deterministic pipe-separated string | `name, course, date, cert_id, normalize_name_case` | `str` |
| `generate_cert_hash()` | SHA-256 of canonical payload | `name, course, date, cert_id, **kwargs` | `str` |

**Key Design**: The `normalize_name_case` parameter (default `False`) preserves name case while lowercasing all other fields. This allows names to retain their original case while ensuring course/date/ID matching is case-insensitive.

**Used by**: `test_ocr.py`

**Not used by**: `app.py` (has its own simple hash function)

---

## `test_ocr.py` — Standalone Test Script

**Purpose**: Standalone test script that exercises the refactored modules (OCR extraction, canonical hashing, blockchain). Can be run independently from the project root.

**File Path**: `c:\Projects\certificateproject\test_ocr.py`

**Lines**: 55

**Execution Flow**:
1. Optionally extract text from `test_images/sample.png`
2. If no image available, use hardcoded dummy certificate text
3. Extract fields: `extract_details(text)`
4. Generate hash: `generate_cert_hash(name, course, date, cert_id)`
5. Initialize blockchain: `Blockchain()`
6. Validate chain: `validate_chain()`
7. Check if hash exists on chain: `find_block_by_cert_hash()`

**Imports**: `models.ocr`, `utils.cert_hash`, `blockchain`

**Status**: Run manually for testing. Not part of an automated test suite.

---

## `templates/base.html` — Base Template

**Purpose**: Base HTML template with common layout elements (navbar, loader, CSS links). Used by all other templates via Jinja2 inheritance.

**File Path**: `c:\Projects\certificateproject\templates\base.html`

**Lines**: 63

**Key Elements**:
- Google Fonts: Inter (300, 400, 600, 700, 800)
- CSS: `style.css`, `animations.css`, `main.css`
- Navbar: "🔐 CertiChain" logo, Home/Issue/Verify links
- Loader: Animated blockchain rings with "Securing Trust..." text
- Content block: `{% block content %}{% endblock %}`
- Loader auto-hide script on `window.load`

---

## `templates/index.html` — Home Page (SPA Shell)

**Purpose**: Modern SPA-style home page shell. Loads Tailwind CSS v4 assets and provides a React-like root div.

**File Path**: `c:\Projects\certificateproject\templates\index.html`

**Lines**: 18

**Key Elements**:
- Title: "Smart Certificate Authentication"
- Tailwind CSS: `assets/index-B161kKw8.css`
- Tailwind JS: `assets/index-CRd-Min5.js`
- Root div: `<div id="root"></div>` for React-like rendering

---

## `templates/issue.html` — Issue Certificate Form

**Purpose**: Upload form for certificate issuance. Extends `base.html`.

**File Path**: `c:\Projects\certificateproject\templates\issue.html`

**Lines**: 17

**Key Elements**:
- Title: "Issue New Certificate"
- File input: accepts `.pdf`, `.png`, `.jpg`, `.jpeg`, `image/*`, `application/pdf`
- Submit button: "Generate & Store"
- Posts to `url_for('issue')`

---

## `templates/verify.html` — Verify Certificate Form

**Purpose**: Upload form for certificate verification. Extends `base.html`.

**File Path**: `c:\Projects\certificateproject\templates\verify.html`

**Lines**: 14

**Key Elements**:
- Title: "Verify Certificate"
- File input: required
- Submit button: "Verify Now"

---

## `templates/upload.html` — Legacy Upload Form

**Purpose**: Simple legacy upload form (no base template inheritance). Minimal styling.

**File Path**: `c:\Projects\certificateproject\templates\upload.html`

**Lines**: 15

**Key Elements**:
- Title: "Upload Certificate for Verification"
- Error display: `{% if error %}`
- Posts to `url_for('verify')`

---

## `templates/result.html` — Result Display

**Purpose**: Displays the result of certificate issuance or verification. Extends `base.html`.

**File Path**: `c:\Projects\certificateproject\templates\result.html`

**Lines**: 20

**Key Elements**:
- Status display (e.g., "ISSUED SUCCESSFULLY", "VERIFIED", "FAKE")
- Certificate details: Name, Course, Date, Certificate ID
- SHA-256 hash in styled box

---

## `static/css/style.css` — Main Custom Stylesheet

**Purpose**: Primary custom stylesheet for the application. Defines global styles, navbar, hero section, buttons, feature cards, forms, and result page.

**File Path**: `c:\Projects\certificateproject\static\css\style.css`

**Lines**: 162

**Key Sections**:
- Global reset and body styling (dark theme: `#0B1120` background)
- Navbar styling (glassmorphism, blur backdrop)
- Hero section (centered, large heading)
- Button styles (primary gradient, secondary)
- Feature cards (dark background, hover effects)
- Form container (centered, dark card)
- Result card and status colors (green for valid, red for fake)

---

## `static/css/animations.css` — Animation Styles

**Purpose**: Loader animation and fade-in effects.

**File Path**: `c:\Projects\certificateproject\static\css\animations.css`

**Lines**: 94

**Key Animations**:
- Blockchain loader: Two pulsing rings with a glowing core
- Typing effect: "Securing Trust..." with cursor blink
- Fade-in on scroll: Opacity + translateY

---

## `static/css/main.css` — Additional Custom Styles

**Purpose**: Additional button styles, glass card effects, and hash box display.

**File Path**: `c:\Projects\certificateproject\static\css\main.css`

**Lines**: 83

**Key Sections**:
- Button variants (primary: cyan, secondary: pink)
- Feature cards (glassmorphism, backdrop blur)
- Glass card (translucent, blurred background)
- Hash box (dark background, cyan text, word-break)

---

## `static/js/main.js` — JavaScript Functionality

**Purpose**: Vanilla JavaScript for loader management and scroll-based fade-in effects.

**File Path**: `c:\Projects\certificateproject\static\js\main.js`

**Lines**: 43

**Key Functionality**:
- Loader auto-hide after 1.2 seconds
- Intersection Observer for fade-in elements (threshold 0.2)

---

## `static/assets/index-B161kKw8.css` — Tailwind CSS Compiled

**Purpose**: Auto-generated Tailwind CSS v4 compiled stylesheet. Contains all utility classes used by the application.

**File Path**: `c:\Projects\certificateproject\static\assets\index-B161kKw8.css`

**Lines**: 1 (minified, very large)

**Content**: Tailwind CSS v4 utilities, custom properties, animations, component styles, dark mode styles, and responsive breakpoints.

---

## `static/assets/index-CRd-Min5.js` — Tailwind UI JS

**Purpose**: Bundled JavaScript for Tailwind UI components (likely shadcn/ui style).

**File Path**: `c:\Projects\certificateproject\static\assets\index-CRd-Min5.js`

**Status**: Minified JavaScript bundle. Contents not inspected in detail.

---

## `requirements.txt` — Python Dependencies

**Purpose**: Lists Python package dependencies for the project.

**File Path**: `c:\Projects\certificateproject\requirements.txt`

**Lines**: 7

**Dependencies**:
```
Flask>=2.0
Pillow>=9.0
pytesseract>=0.3.10
pdf2image>=1.16
```

**Note**: This list is incomplete compared to the actual imports in `app.py`. Missing dependencies include:
- `opencv-python` (cv2)
- `numpy`
- `PyMuPDF` (fitz)
- `python-docx`
- `textract`

---

## `README.md` — Project Documentation

**Purpose**: Project-level documentation explaining setup, usage, and features.

**File Path**: `c:\Projects\certificateproject\README.md`

**Lines**: 40

**Sections**:
- Project description (blockchain-backed ledger)
- Features (persistent blockchain, pattern-based extraction, canonical hashing, chain validation)
- Setup instructions (pip install, Tesseract, Poppler)
- Run instructions (python app.py)
- Project structure reference (ARCHITECTURE.md)
- Possible extensions (digital signatures, QR codes, admin auth, API)

---

## `ARCHITECTURE.md` — Architecture Documentation

**Purpose**: Architecture documentation explaining module roles, design choices, and file layout.

**File Path**: `c:\Projects\certificateproject\ARCHITECTURE.md`

**Lines**: 66

**Sections**:
- Overview
- Major Structural Choices (persistent blockchain, pattern-based extraction, canonical hashing, chain validation, modular layout)
- File layout diagram
- Possible extensions

**Note**: This document describes the **refactored** architecture (routes/, models/, utils/, config/), which is **not yet fully integrated** into the running application.

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [02_DIRECTORY_STRUCTURE.md](02_DIRECTORY_STRUCTURE.md) | Directory structure |
| [04_PIPELINES.md](04_PIPELINES.md) | Pipeline documentation |
| [05_API_REFERENCE.md](05_API_REFERENCE.md) | API endpoint reference |