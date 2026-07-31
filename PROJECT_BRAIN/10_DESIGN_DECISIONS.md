# 10 — DESIGN DECISIONS

## Overview

This document documents the architectural and design decisions made throughout the project. Each decision is categorized as:

- **Confirmed from code**: Directly evidenced in the source code
- **Likely inference**: Reasonable inference based on code patterns and context
- **Unknown**: Cannot be determined from repository inspection

Decisions are never mixed across categories.

---

## Decision Categories

| Category | Count | Description |
|----------|-------|-------------|
| Confirmed from code | 18 | Directly evidenced in source code |
| Likely inference | 6 | Reasonable inference from code patterns |
| Unknown | 3 | Cannot be determined from repository inspection |

---

## Confirmed from Code

### D1: Monolithic Flask Application

**Decision:** All application logic (routes, OCR, extraction, hashing, blockchain) is contained in a single file `app.py`.

**Evidence:** `app.py` contains 935 lines with all functionality defined in module scope. No imports from internal modules (`routes/`, `models/`, `utils/`, `config/`).

**Rationale (inferred):** Likely chosen for simplicity during initial development. The refactored modules (`routes/`, `models/`, `utils/`, `config/`) exist separately but are not integrated.

**Impact:** High coupling, difficult to test individual components, but simple to deploy (single file).

---

### D2: Text-Based Blockchain (blockchain.txt)

**Decision:** Use a plain text file with one SHA-256 hash per line as the primary blockchain storage.

**Evidence:** `app.py` lines 784-797:
```python
BLOCKCHAIN_FILE = "blockchain.txt"
def load_hashes():
    if not os.path.exists(BLOCKCHAIN_FILE):
        return set()
    with open(BLOCKCHAIN_FILE, "r") as f:
        return set(f.read().splitlines())
def add_certificate(cert_hash):
    hashes = load_hashes()
    if cert_hash in hashes:
        return "ALREADY EXISTS"
    with open(BLOCKCHAIN_FILE, "a") as f:
        f.write(cert_hash + "\n")
    return "ISSUED SUCCESSFULLY"
```

**Trade-off:** Simple implementation but no chain validation, no block structure, and vulnerable to tampering.

---

### D3: Two-Stage PDF Extraction

**Decision:** Extract text from PDFs using a two-stage approach: digital text extraction (PyMuPDF) first, then high-DPI OCR fallback if insufficient text.

**Evidence:** `app.py` `_ocr_pdf()` lines 242-366:
- Stage 1: `fitz.open()` → `get_text("blocks")` → check if ≥200 characters
- Stage 2: `pdf2image` at 450 DPI → `_preprocess_for_ocr()` → Tesseract OCR with 3 PSM modes

**Rationale:** Digital text extraction is fast and accurate for born-digital PDFs. OCR fallback handles scanned PDFs. The 200-character threshold balances speed and accuracy.

---

### D4: Multi-PSM OCR Strategy

**Decision:** Run Tesseract with multiple Page Segmentation Modes (PSM) and select the best result.

**Evidence:** `app.py` `_ocr_image_cv()` lines 112-131:
```python
configs = ["--oem 3 --psm 6", "--oem 3 --psm 4", "--oem 3 --psm 3"]
best = ""
for cfg in configs:
    result = pytesseract.image_to_string(processed, config=cfg)
    if len(result.strip()) > len(best.strip()):
        best = result
```

**Trade-off:** 3x slower than single-PSM OCR, but more robust across different certificate layouts.

**Note:** Image OCR uses string-length scoring. PDF OCR fallback uses word-count scoring (words with 2+ alphabetic characters). This inconsistency is confirmed from code.

---

### D5: Aggressive Image Preprocessing

**Decision:** Apply a 6-stage image preprocessing pipeline before OCR: upscale, grayscale, Gaussian blur, Non-Local Means denoising, deskew, Otsu binarization.

**Evidence:** `app.py` `_preprocess_for_ocr()` lines 73-109.

**Rationale:** Each stage addresses a specific OCR challenge:
- Upscaling: Improves character recognition for small images
- Denoising: Reduces noise from scanning/compression
- Deskew: Corrects rotated scanned documents
- Binarization: Converts to ideal black-on-white for Tesseract

---

### D6: Pattern-Based Extraction (app.py)

**Decision:** Use multiple strategies with fallbacks for each certificate field extraction.

**Evidence:** `app.py` extraction functions (lines 443-716):
- Name: 3 strategies (label → trigger phrase → fallback heuristic)
- Course: 3 strategies (label → degree pattern → trigger phrase scan)
- Date: 2 strategies (label → regex patterns)
- Cert ID: 3 strategies (label → regex → URL patterns)
- University: 1 strategy (keyword scoring)
- Year: 1 strategy (regex)

**Rationale:** Defense in depth — if one strategy fails, the next may succeed.

---

### D7: No Hash Normalization

**Decision:** Hash certificate fields without normalization (whitespace, case, etc.).

**Evidence:** `app.py` `generate_hash()` lines 771-781:
```python
data_string = name + "|" + course + "|" + university + "|" + date + "|" + cert_id
cert_hash = hashlib.sha256(data_string.encode()).hexdigest()
```

**Impact:** The same certificate OCR'd differently (e.g., extra spaces, different line breaks) will produce different hashes, causing verification failures. The refactored `utils/cert_hash.py` addresses this with normalization, but it's not used.

---

### D8: File Extension-Only Validation

**Decision:** Validate uploaded files only by their extension, not by content.

**Evidence:** `app.py` `allowed_file()` lines 37-44:
```python
ext = filename.rsplit(".", 1)[1].lower()
return ext in ALLOWED_EXTENSIONS
```

**Security impact:** Files with incorrect extensions bypass validation. No MIME type or magic byte checking.

---

### D9: GET /issue Returns Home Page

**Decision:** The GET handler for `/issue` returns `index.html` (home page) instead of `issue.html` (issue form).

**Evidence:** `app.py` line 839:
```python
return render_template("index.html")  # Should be "issue.html"
```

**Impact:** Users cannot access the issue form via GET /issue — they are redirected to the home page. Confirmed as a likely bug.

---

### D10: GET /verify Returns Home Page

**Decision:** Same as D9 — the GET handler for `/verify` returns `index.html` instead of `verify.html`.

**Evidence:** `app.py` line 864:
```python
return render_template("index.html")  # Should be "verify.html"
```

---

### D11: Dual Blockchain Implementations

**Decision:** Maintain two separate blockchain implementations: a simple text-based one in `app.py` and a structured one in `blockchain.py`.

**Evidence:**
- `app.py` uses `blockchain.txt` with `load_hashes()`, `add_certificate()`, `verify_certificate()`
- `blockchain.py` uses `blockchain.json` with `Block` and `Blockchain` classes

**Impact:** The `blockchain.py` implementation is more robust (chain validation, block structure, legacy migration) but is not used by the active routes.

---

### D12: Dual Hashing Implementations

**Decision:** Maintain two separate hashing implementations: a simple one in `app.py` and a canonical one in `utils/cert_hash.py`.

**Evidence:**
- `app.py` `generate_hash()` uses 5 fields with no normalization
- `utils/cert_hash.py` `generate_cert_hash()` uses 4 fields with normalization

**Impact:** The canonical version is more reliable across different OCR outputs but is not used by the active routes.

---

### D13: Debug Mode Enabled

**Decision:** Run the Flask application with `debug=True`.

**Evidence:** `app.py` line 935:
```python
app.run(debug=True)
```

**Security impact:** Debug mode exposes the Werkzeug debugger with interactive code execution, detailed error pages, and auto-reload. Not suitable for production.

---

### D14: No Authentication

**Decision:** The application has no authentication mechanism.

**Evidence:** No login routes, no user model, no auth decorators, no session management.

**Impact:** Anyone with network access to the application can issue certificates.

---

### D15: Hardcoded Poppler Path

**Decision:** Hardcode the Poppler binary path for Windows.

**Evidence:** `app.py` line 256:
```python
poppler_path = r"C:\poppler\Library\bin\poppler-25.12.0\Library\bin"
```

**Impact:** Not portable to other systems. The refactored `models/ocr.py` uses `POPPLER_PATH` environment variable as a better alternative.

---

### D16: Legacy Migration Support

**Decision:** Automatically migrate from legacy `issue_certificate.json` format to the new `blockchain.json` format.

**Evidence:** `blockchain.py` `_load_legacy()` lines 140-172 and `_load_or_create()` lines 120-138.

**Rationale:** Backward compatibility with data from earlier versions.

---

### D17: Chain Auto-Repair

**Decision:** On validation failure, attempt one-time reindex/relink/rehash of the chain.

**Evidence:** `blockchain.py` `__init__()` lines 108-117:
```python
if not self.validate_chain():
    prev_hash = "0"
    for i, block in enumerate(self.chain):
        block.index = i
        block.previous_hash = prev_hash
        block.hash = block._calculate_hash()
        prev_hash = block.hash
    self.save()
    if not self.validate_chain():
        raise ValueError("Blockchain integrity check failed.")
```

**Rationale:** Graceful recovery from data corruption or format changes.

---

### D18: Deep Copy for Data Immutability

**Decision:** Use `copy.deepcopy()` for block data to prevent mutation.

**Evidence:** `blockchain.py` lines 46, 72:
```python
self._data = copy.deepcopy(data) if isinstance(data, dict) else data
```

---

## Likely Inference

### I1: Progressive Enhancement

**Inference:** The project was developed incrementally, starting with `app_backup.py` and evolving to `app.py`, then refactoring into separate modules.

**Evidence:**
- `app_backup.py` has simpler OCR, simpler extraction, and more limited file types
- `app.py` has advanced preprocessing, multi-PSM OCR, and more extraction strategies
- `models/`, `routes/`, `utils/`, `config/` represent a further refactoring that was never completed

**Confidence:** High — the progression from simple to complex is clear.

---

### I2: Refactoring Was Incomplete

**Inference:** The developer began refactoring `app.py` into separate modules (`routes/`, `models/`, `utils/`, `config/`) but did not complete the integration.

**Evidence:**
- `routes/upload.py` and `routes/verify.py` define Blueprints but are not registered with the Flask app
- `models/ocr.py` and `config/extraction_patterns.py` are not imported by `app.py`
- `utils/cert_hash.py` is not used by `app.py`
- `blockchain.py` is not used by `app.py`
- `ARCHITECTURE.md` describes the refactored architecture, not the actual running architecture

**Confidence:** High — the refactored modules exist but are disconnected from the main application.

---

### I3: React/Tailwind UI Integration

**Inference:** The UI was built with a modern frontend framework (likely React with Tailwind CSS v4) and the compiled assets were placed in `static/assets/`.

**Evidence:**
- `templates/index.html` has `<div id="root"></div>` and loads `index-CRd-Min5.js`
- `static/assets/index-B161kKw8.css` is a Tailwind CSS v4 compiled stylesheet
- `templates/base.html` has separate CSS files (`style.css`, `animations.css`, `main.css`)

**Confidence:** High — the SPA shell pattern and Tailwind v4 asset naming are definitive.

---

### I4: The `issue.html` and `verify.html` Templates Are Legacy

**Inference:** The `issue.html` and `verify.html` templates (which extend `base.html`) are from an earlier version of the UI, while `index.html` (which loads Tailwind assets) represents the newer SPA-based UI.

**Evidence:**
- `issue.html` and `verify.html` extend `base.html` with simple forms
- `index.html` uses a completely different approach (SPA shell with `<div id="root">`)
- The GET handlers for `/issue` and `/verify` return `index.html` (the new UI), not `issue.html` or `verify.html`

**Confidence:** Medium — the inconsistency in template rendering suggests a transitional state.

---

### I5: The `analysis/` and `extraction/` Directories Contained Source Files

**Inference:** The `analysis/` and `extraction/` directories once contained Python source files that have since been deleted.

**Evidence:**
- Both directories contain `__pycache__/` with `.pyc` files (compiled bytecode)
- `analysis/__pycache__/` has `info_extractor.cpython-313.pyc` and `scorer.cpython-313.pyc`
- `extraction/__pycache__/` has `ocr_engine.cpython-313.pyc`, `pdf_parser.cpython-313.pyc`, and `reconciler.cpython-313.pyc`
- No `.py` source files exist in these directories

**Confidence:** High — `.pyc` files are only generated from `.py` source files.

---

### I6: Test-Driven Development Was Not Used

**Inference:** The project was developed without a formal test-driven development approach.

**Evidence:**
- Only one test script exists (`test_ocr.py`)
- `test_ocr.py` is a manual test script, not an automated test suite
- No `pytest` or `unittest` configuration
- No test fixtures beyond the empty `test_images/` directory

**Confidence:** High — the absence of a test framework and automated tests is clear.

---

## Unknown

### U1: Purpose of `.orchids/` Directory

**Unknown:** The purpose of the `.orchids/` directory and `orchids.json` file cannot be determined from repository inspection.

**Evidence:** The `.orchids/` directory contains a single `orchids.json` file. No references to "orchids" exist in any source code, configuration, or documentation files.

---

### U2: Purpose of `results/` Directory

**Unknown:** The intended use of the `results/` directory cannot be determined from repository inspection.

**Evidence:** The directory exists and is empty. No code writes to this directory. No documentation references it.

---

### U3: Original Developer Identity

**Unknown:** The identity of the original developer cannot be determined from repository inspection.

**Evidence:** No `.git` directory exists. No author information is present in source files. The `cursor_access_test.txt` file suggests the project was edited with Cursor IDE.

---

## Decision Impact Matrix

| Decision | Impact | Risk | Reversibility |
|----------|--------|------|---------------|
| Monolithic app.py | High coupling, hard to test | Medium | Low (requires refactoring) |
| Text-based blockchain | No integrity, no structure | High | Low (requires migration) |
| Two-stage PDF extraction | Good PDF coverage | Low | High (easy to change) |
| Multi-PSM OCR | 3x slower but more robust | Low | High (easy to change) |
| Aggressive preprocessing | Better OCR accuracy | Low | High (easy to change) |
| No hash normalization | Verification failures on OCR variation | High | Low (changes all hashes) |
| Extension-only validation | Security vulnerability | High | High (easy to add) |
| No authentication | Anyone can issue certificates | Critical | High (easy to add) |
| Debug mode enabled | Code execution risk | Critical | High (easy to disable) |
| Dual implementations | Confusion, maintenance burden | Medium | Low (requires consolidation) |
| Hardcoded paths | Not portable | Medium | High (easy to change) |

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [11_CURRENT_STATUS.md](11_CURRENT_STATUS.md) | Current project status |
| [12_TODO_ROADMAP.md](12_TODO_ROADMAP.md) | Prioritized roadmap |