# Certificate Authentication System — Architecture

## Overview

The system verifies certificate authenticity using a **blockchain-backed ledger**: when a certificate is issued, a hash of its key fields is stored in a block; verification checks whether that hash exists in the chain.

## Major Structural Choices

### 1. Persistent blockchain (`blockchain.json`)

- **Before:** The app used an in-memory chain; a separate `blockchain.py` wrote to `issue_certificate.json` with a different format, and the Flask app did not use it.
- **After:** A single `blockchain.py` defines `Block` and `Blockchain`. On startup, the chain is **loaded from `blockchain.json`** (same directory as the project). After each new certificate is issued, the chain is **saved** to the same file. Block structure is consistent: `index`, `timestamp`, `data` (certificate payload), `previous_hash`, `hash`.

### 2. Pattern-based extraction (no hardcoded certificate text)

- **Before:** `extract_details()` in `models/ocr.py` relied on fixed phrases like `"presented to"` and `"complet"` for name and course.
- **After:** All extraction logic is **pattern-based**. Patterns live in `config/extraction_patterns.py`: lists of trigger phrases, label keywords, regexes, and fallback rules. Adding a new institution or layout is done by extending these lists (e.g. new “name” triggers or “course” labels) without changing OCR code. No certificate-specific text is hardcoded in the extractor.

### 3. Canonical hashing and verification

- **Before:** Raw string `name|course|date|cert_id` was hashed in the app; normalization was inconsistent.
- **After:** `utils/cert_hash.py` provides `build_canonical_payload()` and `generate_cert_hash()`. Fields are normalized (whitespace collapsed, stripped) so minor OCR differences produce the same hash when issuing and verifying. Both issue and verify use the same canonical hash.

### 4. Chain validation

- On load, `Blockchain.validate_chain()` checks that every block’s `hash` and `previous_hash` link correctly. This improves verification reliability by ensuring the stored chain is intact before any lookup.

### 5. Modular layout

| Layer        | Role |
|-------------|------|
| `app.py`    | Flask routes only; uses blockchain, OCR, and cert hash utils. |
| `blockchain.py` | Block/Blockchain, load/save to `blockchain.json`, `find_block_by_cert_hash()`, `validate_chain()`. |
| `config/extraction_patterns.py` | All patterns for date, ID, name, course (triggers, labels, regexes). |
| `models/ocr.py` | `extract_text()` (image/PDF → text), `extract_details()` (text → name, course, date, cert_id) using config patterns. |
| `utils/cert_hash.py` | Canonical payload string and SHA-256 cert hash. |

## File layout

```
certificateproject/
├── app.py                    # Flask app, routes
├── blockchain.py             # Chain persistence and verification
├── blockchain.json           # Persisted chain (created on first run)
├── config/
│   ├── __init__.py
│   └── extraction_patterns.py
├── models/
│   └── ocr.py
├── utils/
│   ├── __init__.py
│   └── cert_hash.py
├── templates/
├── uploads/
├── requirements.txt
└── ARCHITECTURE.md
```

## Possible extensions (not implemented)

- Digital signature support  
- QR code verification  
- Admin authentication  
- API endpoint for verification (e.g. POST /api/verify with file or hash)

These can be added on top of the current structure without changing the core blockchain or extraction design.
