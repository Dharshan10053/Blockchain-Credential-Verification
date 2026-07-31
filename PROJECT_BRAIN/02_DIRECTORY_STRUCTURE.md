# 02 — DIRECTORY STRUCTURE

## Complete Directory Tree

```
C:\Projects\certificateproject\
│
├── app.py                              # Main Flask application (primary entry point)
├── app_backup.py                       # Backup copy of earlier version of app.py
├── blockchain.py                       # Full Block/Blockchain class implementation with JSON persistence
├── blockchain.json                     # Persisted blockchain chain data (auto-generated)
├── blockchain.txt                      # Simple text-based blockchain (used by app.py routes)
├── db.json                             # Legacy KV store (used by models/certificate_store.py)
├── issue_certificate.json              # Legacy certificate storage (auto-migrated by blockchain.py)
├── ocr_utils.py                        # Simple OCR utility module (legacy/standalone)
├── test_ocr.py                         # Standalone test script for OCR extraction and blockchain
│
├── requirements.txt                    # Python dependencies
├── README.md                           # Project documentation
├── ARCHITECTURE.md                     # Architecture documentation
│
├── extraction_system.log               # Application log file (Flask debug logs)
├── cursor_access_test.txt              # Test file for cursor tool access
│
├── .agents/                            # AI agent configuration files
│   ├── rules/
│   │   └── graphify.md                 # Graphify knowledge graph rules for AI agents
│   └── workflows/
│       └── graphify.md                 # Graphify workflow definition
│
├── .orchids/
│   └── orchids.json                    # Orchids configuration (unknown purpose)
│
├── analysis/                           # Analysis module (only .pyc cache files, no source)
│   └── __pycache__/
│       ├── info_extractor.cpython-313.pyc
│       └── scorer.cpython-313.pyc
│
├── config/                             # Pattern-based extraction configuration
│   ├── __init__.py                     # Exports pattern functions
│   └── extraction_patterns.py          # All extraction patterns (dates, IDs, names, courses)
│
├── extraction/                         # Extraction module (only .pyc cache files, no source)
│   └── __pycache__/
│       ├── ocr_engine.cpython-313.pyc
│       ├── pdf_parser.cpython-313.pyc
│       └── reconciler.cpython-313.pyc
│
├── graphify-out/                       # Graphify knowledge graph output
│   ├── .graphify_labels.json
│   ├── .graphify_python
│   ├── .graphify_root
│   ├── GRAPH_REPORT.md
│   ├── graph.html
│   ├── graph.json
│   ├── manifest.json
│   ├── cost.json
│   └── cache/
│       └── ast/                        # AST cache files for graphify
│
├── models/                             # Model layer (refactored modules)
│   ├── __init__.py                     # Empty init
│   ├── certificate_store.py           # Simple JSON-based KV store for certificate verification
│   ├── hash_utils.py                  # Simple hash utility (normalize + SHA-256)
│   └── ocr.py                         # Pattern-based OCR extraction using config patterns
│
├── myenv/                              # Python virtual environment
├── venv/                               # Python virtual environment (alternative)
│
├── results/                            # Results directory (empty)
│
├── routes/                             # Flask Blueprint routes (refactored)
│   ├── upload.py                       # Upload blueprint (GET /, POST /upload)
│   └── verify.py                       # Verify blueprint (POST /) using models
│
├── static/                             # Static files (CSS, JS, assets)
│   ├── css/
│   │   ├── style.css                   # Main custom stylesheet
│   │   ├── animations.css              # Loader animation styles
│   │   └── main.css                    # Additional custom styles
│   ├── js/
│   │   └── main.js                     # Vanilla JS (loader, fade-in effects)
│   └── assets/
│       ├── index-B161kKw8.css          # Tailwind CSS v4 compiled stylesheet
│       └── index-CRd-Min5.js           # Tailwind UI component JS (bundled)
│
├── templates/                          # Jinja2 HTML templates
│   ├── base.html                       # Base template with navbar, loader, layout
│   ├── index.html                      # Home page (React SPA shell)
│   ├── issue.html                      # Issue certificate form
│   ├── verify.html                     # Verify certificate form
│   ├── upload.html                     # Legacy upload form (simple HTML)
│   └── result.html                     # Issue/Verification result display
│
├── test_images/                        # Test image fixtures (empty)
│
└── uploads/                            # Uploaded certificate files (runtime)
```

## Folder Responsibilities

### Root Directory

| Item | Type | Responsibility |
|------|------|---------------|
| `app.py` | File | **Primary application entry point**. Contains Flask initialization, all routes (web + API), OCR pipeline, field extraction, hash generation, and blockchain operations. This is the main file executed to run the application. |
| `app_backup.py` | File | **Backup of an earlier version** of `app.py`. Contains a simpler implementation with basic image preprocessing, OCR, field extraction, and the same routes. Uses `blockchain.txt` for hash storage. |
| `blockchain.py` | File | **Full blockchain implementation** with `Block` and `Blockchain` classes. Provides chain validation, block structure (index, timestamp, data, previous_hash, hash), JSON persistence to `blockchain.json`, legacy migration from `issue_certificate.json`, and `find_block_by_cert_hash()` lookup. |
| `blockchain.json` | File | **Persisted blockchain data** (auto-generated). Contains the chain of blocks in JSON format. Created by `blockchain.py` on first run. |
| `blockchain.txt` | File | **Simple text-based blockchain** used by `app.py` routes. Contains one SHA-256 hash per line. Each line represents a certificate stored in the chain. |
| `db.json` | File | **Legacy KV store** used by `models/certificate_store.py`. Maps certificate IDs to hash values. Not used by the main `app.py`. |
| `issue_certificate.json` | File | **Legacy certificate storage** from an earlier version of the application. Contains a flat list of certificate records with index, timestamp, certificate_id, name, course, date, hash, and previous_hash. Automatically migrated to `blockchain.json` by `blockchain.py` if the new format doesn't exist. |
| `ocr_utils.py` | File | **Simple standalone OCR utility**. Sets Tesseract path and provides a basic `extract_text()` function using PIL + pytesseract. Not integrated into the main application. |
| `test_ocr.py` | File | **Standalone test script** that exercises the refactored modules (`models.ocr`, `utils.cert_hash`, `blockchain.py`). Tests extraction, hashing, and blockchain lookup. Uses dummy text or a test image. |
| `requirements.txt` | File | **Python package dependencies** for the project. Lists Flask, Pillow, pytesseract, pdf2image. |
| `README.md` | File | **Project documentation** explaining setup, usage, and features. |
| `ARCHITECTURE.md` | File | **Architecture documentation** explaining module roles, design choices, and file layout. |
| `extraction_system.log` | File | **Application log file** containing Flask debug output, including requests, errors, and server restarts. |
| `cursor_access_test.txt` | File | **Test file** for verifying cursor/editor tool access. |

---

### `config/` — Configuration Module

**Purpose**: Centralized configuration for extraction patterns. All certificate field detection patterns are defined here, allowing different layouts and institutions to be supported by adding patterns rather than changing code.

**Responsibility**: Provide pattern lists and configuration dictionaries for date, ID, name, and course extraction.

**Files**:

| File | Purpose |
|------|---------|
| `__init__.py` | Package init. Re-exports `get_date_patterns()`, `get_id_patterns()`, `get_name_patterns()`, `get_course_patterns()` from `extraction_patterns.py`. |
| `extraction_patterns.py` | Contains all extraction patterns: date regex patterns (5 date formats), ID patterns (regex + label keywords), name patterns (trigger phrases, labels, fallback exclusions), course patterns (trigger phrases, labels, validation rules). |

**Used by**: `models/ocr.py` (imports all pattern functions)

**Not used by**: `app.py` (has its own hardcoded extraction logic)

**Risk if modified**: Incorrect pattern changes could cause extraction failures for all certificate types. Changes should be tested with representative certificate samples.

---

### `models/` — Model Layer (Refactored)

**Purpose**: Data models and business logic for OCR, hashing, and certificate storage. These are the refactored modules that separate concerns from the monolithic `app.py`.

**Responsibility**: Provide OCR text extraction, field extraction using configurable patterns, hash generation, and certificate verification.

**Files**:

| File | Purpose |
|------|---------|
| `__init__.py` | Empty init file. |
| `ocr.py` | **OCR and extraction module**. Provides `extract_text()` (image/PDF → text using Tesseract) and `extract_details()` (text → name, course, date, cert_id, full_text). Uses patterns from `config/extraction_patterns.py`. Has fallback strategies for each field. |
| `hash_utils.py` | **Simple hash utility**. Provides `normalize_text()` (lowercase, collapse whitespace, remove non-alphanumeric) and `generate_hash()` (SHA-256). |
| `certificate_store.py` | **Simple JSON-based KV store**. Provides `load_db()`, `save_db()`, `add_certificate()`, `verify_certificate()` using a local `db.json` file. Maps certificate ID to hash value. |

**Dependencies**: `config/`, `pytesseract`, `PIL`, `pdf2image`, `hashlib`, `json`, `os`

**Used by**: `routes/verify.py` (imports `extract_text`, `extract_details`, `generate_hash`, `verify_certificate`)

**Not used by**: `app.py` (has its own implementations)

**Risk if modified**: Changes to `ocr.py` affect all routes using the refactored blueprint (`routes/verify.py`). Breaking changes to extraction functions could cause verification failures.

---

### `routes/` — Flask Blueprint Routes (Refactored)

**Purpose**: Separated route handlers using Flask Blueprints. These are intended to replace the monolithic routes in `app.py`.

**Responsibility**: Handle HTTP requests for certificate upload and verification.

**Files**:

| File | Purpose |
|------|---------|
| `upload.py` | **Upload Blueprint**. Provides `GET /` (renders upload form) and `POST /upload` (saves certificate file, renders verify page). Uses `werkzeug.secure_filename` for file sanitization. |
| `verify.py` | **Verify Blueprint**. Provides `POST /` (accepts filepath, runs OCR, extracts fields, generates hash, verifies against store, renders result). Imports from `models/ocr`, `models/hash_utils`, `models/certificate_store`. |

**Dependencies**: `flask`, `werkzeug`, `models/`, `os`

**Not used by**: `app.py` (blueprints are not registered with the Flask app)

**Risk if modified**: These blueprints are not active in the current application. Modifications have no runtime effect until they are registered with the Flask app.

---

### `utils/` — Utility Modules (Refactored)

**Purpose**: Shared utilities for canonical certificate representation and hashing.

**Responsibility**: Provide deterministic hash generation that normalizes field values to ensure consistency across issue and verify operations.

**Files**:

| File | Purpose |
|------|---------|
| `__init__.py` | Package init. Re-exports `build_canonical_payload()` and `generate_cert_hash()` from `cert_hash.py`. |
| `cert_hash.py` | **Canonical hash utility**. Provides `_normalize_field()` (whitespace collapse, optional lowercase), `build_canonical_payload()` (name|course|date|cert_id with normalization), `generate_cert_hash()` (SHA-256 of canonical payload). |

**Used by**: `test_ocr.py` (imports `generate_cert_hash`)

**Not used by**: `app.py`, `routes/`, `models/`

---

### `static/` — Static Web Assets

**Purpose**: Serve CSS, JavaScript, and compiled assets to the web browser.

**Responsibility**: Provide styling, animations, and interactivity for the web UI.

**Files**:

| File | Purpose |
|------|---------|
| `css/style.css` | **Main custom stylesheet**. Defines global styles, navbar, hero section, buttons, feature cards, forms, result page, status colors. ~162 lines. |
| `css/animations.css` | **Animation styles**. Defines loader animation (pulsing rings, typing effect), fade-in on scroll. ~94 lines. |
| `css/main.css` | **Additional custom styles**. Button styles, feature cards, glass card, hash box display. ~83 lines. |
| `js/main.js` | **Vanilla JavaScript**. Loader system (auto-hide after 1.2s), fade-in observer on scroll. ~43 lines. |
| `assets/index-B161kKw8.css` | **Tailwind CSS v4 compiled stylesheet**. Auto-generated by Tailwind build process. Large file with all utility classes. |
| `assets/index-CRd-Min5.js` | **Tailwind UI component JavaScript**. Bundled JS for UI components (likely shadcn/ui style). |

**Dependencies**: None (standalone)

**Loaded by**: `templates/base.html` (loads CSS files), `templates/index.html` (loads Tailwind assets)

---

### `templates/` — Jinja2 HTML Templates

**Purpose**: Server-side rendered HTML templates for the web UI.

**Responsibility**: Provide the user interface for certificate issuance, verification, and results display.

**Files**:

| File | Purpose |
|------|---------|
| `base.html` | **Base template**. Contains HTML structure, Google Fonts import, CSS links, navbar (CertiChain logo, Home/Issue/Verify links), loader animation, content block. Used by all other templates via Jinja2 inheritance. |
| `index.html` | **Home page**. Modern SPA-style shell that loads Tailwind assets (`index-B161kKw8.css`, `index-CRd-Min5.js`). Contains a `<div id="root"></div>` for React-like rendering. |
| `issue.html` | **Issue certificate form**. Extends `base.html`. Contains file upload input (accepts .pdf, .png, .jpg, .jpeg) and "Generate & Store" submit button. Posts to `url_for('issue')`. |
| `verify.html` | **Verify certificate form**. Extends `base.html`. Contains file upload input and "Verify Now" submit button. |
| `upload.html` | **Legacy upload form**. Simple HTML page (no base template inheritance). Contains file upload form that posts to `url_for('verify')`. Minimal styling. |
| `result.html` | **Result display page**. Extends `base.html`. Displays verification/issuance status, certificate details (name, course, date, cert_id), and SHA-256 hash in a styled box. |

**Dependencies**: `flask` (Jinja2), `static/` (CSS, JS)

**Rendered by**: `app.py` routes, `routes/upload.py`, `routes/verify.py`

---

### `analysis/` — Analysis Module

**Purpose**: Certificate analysis functionality (source files deleted, only `.pyc` cache remains).

**Files**: Only compiled Python cache files exist:
- `__pycache__/info_extractor.cpython-313.pyc`
- `__pycache__/scorer.cpython-313.pyc`

**Status**: **Source files are missing**. The `.pyc` files indicate that Python source files (`info_extractor.py`, `scorer.py`) once existed but have been deleted. The cached bytecode may still be loadable but the module is not functional for development.

---

### `extraction/` — Extraction Module

**Purpose**: Certificate extraction functionality (source files deleted, only `.pyc` cache remains).

**Files**: Only compiled Python cache files exist:
- `__pycache__/ocr_engine.cpython-313.pyc`
- `__pycache__/pdf_parser.cpython-313.pyc`
- `__pycache__/reconciler.cpython-313.pyc`

**Status**: **Source files are missing**. The `.pyc` files indicate that Python source files (`ocr_engine.py`, `pdf_parser.py`, `reconciler.py`) once existed but have been deleted. The cached bytecode may still be loadable but the module is not functional for development.

---

### `graphify-out/` — Graphify Knowledge Graph Output

**Purpose**: Auto-generated knowledge graph data for the project, created by the Graphify tool. Used by AI agents for codebase navigation.

**Files**: Contains graph data (JSON, HTML), manifest, cost tracking, and AST cache files.

**Status**: Development tool output. Not part of the application runtime. Can be safely ignored for production deployment.

---

### `uploads/` — Uploaded Certificate Files

**Purpose**: Runtime storage for certificate files uploaded by users during issue and verify operations.

**Status**: Created automatically on first run. Contents are runtime-only and not committed to version control (should be in `.gitignore`).

---

### `test_images/` — Test Image Fixtures

**Purpose**: Directory for test certificate images used by `test_ocr.py`.

**Status**: Currently empty. The test script checks for `test_images/sample.png` and uses dummy text if not found.

---

### `results/` — Results Directory

**Purpose**: Directory for storing output results (intended use).

**Status**: Currently empty. No files are written to this directory by any current code path.

---

### `myenv/` and `venv/` — Python Virtual Environments

**Purpose**: Isolated Python environments with installed dependencies.

**Status**: Two virtual environments exist (`myenv/` and `venv/`). Both contain `pip`, `python`, and installed packages. The `venv/` environment appears to be the more complete one with all required packages.

---

### `.agents/` — AI Agent Configuration

**Purpose**: Configuration files for AI coding agents (Cline, Claude, etc.) that work with this repository.

**Files**:
- `rules/graphify.md`: Rules for AI agents to use the Graphify knowledge graph when answering codebase questions.
- `workflows/graphify.md`: Workflow definition for running the Graphify pipeline.

**Status**: Development tooling. Not part of the application runtime.

---

### `.orchids/` — Orchids Configuration

**Purpose**: Configuration for the Orchids tool (purpose unknown from repository inspection).

**Files**:
- `orchids.json`: JSON configuration file.

**Status**: Unknown from repository inspection. Not referenced by any application code.

---

## Directory Dependency Graph

```
app.py
├── static/ (serving CSS/JS)
├── templates/ (Jinja2 rendering)
└── uploads/ (file I/O) [runtime]

config/
└── models/ocr.py → config/extraction_patterns.py

models/
├── models/ocr.py → config/ (pattern functions)
└── models/ocr.py → pytesseract, PIL, pdf2image (external)

routes/
├── routes/upload.py → werkzeug, flask
├── routes/verify.py → models/ocr, models/hash_utils, models/certificate_store
└── routes/verify.py → flask, os

utils/
├── utils/cert_hash.py → hashlib, re
└── utils/__init__.py → utils/cert_hash

blockchain.py
├── hashlib, json, os, datetime, copy
├── blockchain.json (file I/O)
└── issue_certificate.json (file I/O, migration)

test_ocr.py
├── models/ocr
├── utils/cert_hash
├── blockchain
└── test_images/ (optional)
```

## Folder Interaction Summary

| Source Folder | Accesses | Purpose |
|---------------|----------|---------|
| `app.py` (root) | `templates/` | Renders HTML templates |
| `app.py` (root) | `static/` | Serves CSS/JS (via Flask) |
| `app.py` (root) | `uploads/` | Saves uploaded files |
| `app.py` (root) | `blockchain.txt` | Reads/writes blockchain |
| `blockchain.py` (root) | `blockchain.json` | Reads/writes blockchain |
| `blockchain.py` (root) | `issue_certificate.json` | Reads legacy data |
| `models/certificate_store.py` | `db.json` | Reads/writes KV store |
| `routes/verify.py` | `models/` | Imports OCR, hash, store |
| `models/ocr.py` | `config/` | Imports pattern functions |
| `test_ocr.py` | `models/`, `utils/`, `blockchain.py` | Imports and tests |

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview and technology stack |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture and module relationships |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference for all important files |
| [07_DEPENDENCIES.md](07_DEPENDENCIES.md) | Dependency analysis |