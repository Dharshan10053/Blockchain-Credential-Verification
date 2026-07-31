# 07 — DEPENDENCIES

## Overview

This document analyzes every dependency used by the Certificate Authentication System, including Python packages, external system tools, and standard library modules. Each dependency is documented with its purpose, why it was chosen, where it's used, criticality, alternatives, and removal impact.

---

## Dependency Categories

| Category | Count | Description |
|----------|-------|-------------|
| Python Packages (external) | 9 | Packages installed via pip |
| System Tools (external) | 2 | OS-level executables |
| Python Standard Library | 8 | Built-in modules |
| Development Tools | 1 | Graphify (knowledge graph) |

---

## Python Package Dependencies

### 1. Flask

| Aspect | Detail |
|--------|--------|
| **Version** | `>=2.0` |
| **Import Name** | `flask` |
| **Purpose** | Web framework for the HTTP server, routing, request handling, template rendering, and JSON response |
| **Why Chosen** | Lightweight, Python-native, extensive ecosystem, easy to set up for small to medium web applications |
| **Where Used** | `app.py` (lines 1, 24, 808-928) — all route handlers, Flask app initialization |
| **Criticality** | **Critical** — The entire application is built on Flask. Without it, no HTTP server exists |
| **Alternatives** | Django (heavier, more opinionated), FastAPI (async, modern), Pyramid (more complex), Bottle (single-file, less ecosystem) |
| **Removal Impact** | Complete application rewrite. All routes, request handling, template rendering, and JSON responses would need to be reimplemented |

### 2. OpenCV (`opencv-python`)

| Aspect | Detail |
|--------|--------|
| **Import Name** | `cv2` |
| **Purpose** | Image processing: reading images, color conversion, resizing, blurring, denoising, deskewing, thresholding |
| **Why Chosen** | Industry-standard computer vision library with comprehensive image processing functions. Required for the preprocessing pipeline that maximizes OCR accuracy |
| **Where Used** | `app.py` (lines 6, 50-109) — `_deskew()`, `_preprocess_for_ocr()`, `_ocr_image_file()`, `_ocr_pdf()` |
| **Criticality** | **High** — Required for image OCR and PDF OCR fallback. Without it, image preprocessing is impossible, severely degrading OCR accuracy |
| **Alternatives** | Pillow (limited image processing, no deskew), scikit-image (less performant), ImageMagick (external process, slower) |
| **Removal Impact** | Image OCR would fail. PDF OCR fallback would fail. The application would only work with digital-text PDFs, DOCX, and DOC files |

### 3. NumPy

| Aspect | Detail |
|--------|--------|
| **Import Name** | `numpy` |
| **Purpose** | Numerical operations for image processing: array manipulation, coordinate calculations, image data representation |
| **Why Chosen** | Required by OpenCV for image representation. All OpenCV images are NumPy arrays |
| **Where Used** | `app.py` (lines 7, 50-109) — `_deskew()` (coordinate operations), `_preprocess_for_ocr()` (image operations), `_ocr_pdf()` (array conversion) |
| **Criticality** | **High** — Required by OpenCV. Without NumPy, OpenCV operations are impossible |
| **Alternatives** | None practical. OpenCV depends on NumPy for array representation |
| **Removal Impact** | Same as OpenCV — image processing fails entirely |

### 4. pytesseract

| Aspect | Detail |
|--------|--------|
| **Import Name** | `pytesseract` |
| **Version** | `>=0.3.10` |
| **Purpose** | Python wrapper for the Tesseract OCR engine. Provides the `image_to_string()` function that extracts text from images |
| **Why Chosen** | Standard Python binding for Tesseract, the most widely used open-source OCR engine |
| **Where Used** | `app.py` (lines 8, 125-130, 140-143, 338-343) — `_ocr_image_cv()`, `_ocr_image_with_layout()`, `_ocr_pdf()` |
| **Criticality** | **Critical** — Without pytesseract, there is no OCR capability. The entire certificate extraction pipeline would fail |
| **Alternatives** | Tesserocr (C extension, faster but harder to install), EasyOCR (deep learning-based, slower), Google Cloud Vision API (external service, cost) |
| **Removal Impact** | All OCR extraction fails. Certificate issuance and verification become impossible for image-based certificates |

### 5. Pillow (PIL)

| Aspect | Detail |
|--------|--------|
| **Import Name** | `PIL` |
| **Version** | `>=9.0` |
| **Purpose** | Image loading, format conversion, and basic image operations. Used to open images for OCR and convert PDF pages to images |
| **Why Chosen** | Standard Python imaging library. Required by pytesseract for image loading, required by pdf2image for PDF page rendering |
| **Where Used** | `app.py` (line 9) — imported but `PIL.Image` is used indirectly through pdf2image; `models/ocr.py` (line 13) — `Image.open()` for OCR |
| **Criticality** | **High** — Required by pytesseract and pdf2image. Without Pillow, images cannot be loaded for OCR |
| **Alternatives** | OpenCV can read images directly (cv2.imread), which `app.py` already uses. However, pdf2image and pytesseract require Pillow |
| **Removal Impact** | pytesseract and pdf2image would fail. PDF and image OCR would be impossible |

### 6. pdf2image

| Aspect | Detail |
|--------|--------|
| **Import Name** | `pdf2image` |
| **Version** | `>=1.16` |
| **Purpose** | Convert PDF pages to PIL Images for OCR. Required for the PDF OCR fallback pipeline |
| **Why Chosen** | Standard library for PDF-to-image conversion. Works with poppler for high-quality rendering |
| **Where Used** | `app.py` (lines 10, 317) — `_ocr_pdf()` converts PDF pages to images at 450 DPI for OCR |
| **Criticality** | **High** — Required for PDF OCR fallback. Without it, scanned PDFs cannot be processed |
| **Alternatives** | PyMuPDF (fitz) can render pages to pixmaps directly (used in `app_backup.py`), pdfplumber (text extraction only), pdfminer (text extraction only) |
| **Removal Impact** | PDF OCR fallback fails. The application would only work with digital-text PDFs (via PyMuPDF) |

### 7. PyMuPDF (fitz)

| Aspect | Detail |
|--------|--------|
| **Import Name** | `fitz` |
| **Purpose** | PDF text extraction and manipulation. Used for digital text extraction from PDFs (first stage of PDF pipeline) |
| **Why Chosen** | Fast, comprehensive PDF handling. Can extract text blocks with layout information |
| **Where Used** | `app.py` (lines 11, 249, 289-300) — `_ocr_pdf()` imports fitz and uses it for digital text extraction |
| **Criticality** | **High** — Required for digital text extraction from PDFs. Without it, the first stage of PDF processing fails |
| **Alternatives** | pdfplumber (text extraction), pdfminer (text extraction), PyPDF2 (basic text extraction) |
| **Removal Impact** | Digital text extraction from PDFs fails. The system would rely entirely on the OCR fallback for PDFs, which is slower and less accurate |

### 8. python-docx

| Aspect | Detail |
|--------|--------|
| **Import Name** | `docx` |
| **Purpose** | Extract text from Microsoft Word DOCX files |
| **Why Chosen** | Standard library for reading DOCX files in Python |
| **Where Used** | `app.py` (lines 219-224) — `_text_from_docx()` imports and uses `docx.Document` |
| **Criticality** | **Low** — Only used for DOCX file support. The core functionality (PDF and image processing) does not depend on it |
| **Alternatives** | zipfile + XML parsing (manual), textract (also handles DOCX), LibreOffice (external conversion) |
| **Removal Impact** | DOCX file uploads would return empty text. Certificate issuance and verification for DOCX files would fail |

### 9. textract

| Aspect | Detail |
|--------|--------|
| **Import Name** | `textract` |
| **Purpose** | Extract text from legacy Microsoft Word DOC files |
| **Why Chosen** | Supports multiple document formats including legacy .doc format |
| **Where Used** | `app.py` (lines 233-237) — `_text_from_doc()` imports and uses `textract.process()` |
| **Criticality** | **Low** — Only used for legacy DOC file support. The library may not be available on all platforms |
| **Alternatives** | antiword (external tool), LibreOffice (external conversion), catdoc (external tool) |
| **Removal Impact** | DOC file uploads would return empty text. Certificate issuance and verification for DOC files would fail |

---

## System Tool Dependencies

### 1. Tesseract OCR

| Aspect | Detail |
|--------|--------|
| **Executable** | `tesseract.exe` |
| **Purpose** | OCR engine that performs the actual text recognition from images |
| **Why Chosen** | Industry-standard open-source OCR engine with extensive language support and configuration options |
| **Where Used** | Called by pytesseract (Python wrapper) in `app.py` `_ocr_image_cv()` and `_ocr_pdf()` |
| **Criticality** | **Critical** — Without Tesseract, no OCR is possible. The entire application purpose is defeated |
| **Installation** | Must be installed separately. Download from GitHub releases. Default path: `C:\Program Files\Tesseract-OCR\` |
| **Alternatives** | EasyOCR (deep learning, slower), Google Cloud Vision (API, cost), Windows OCR (platform-specific) |
| **Removal Impact** | Complete application failure for image-based certificates. Only digital-text PDFs would work |

### 2. Poppler

| Aspect | Detail |
|--------|--------|
| **Executable** | `pdftoppm.exe`, `pdfinfo.exe`, etc. |
| **Purpose** | PDF rendering engine used by pdf2image to convert PDF pages to images |
| **Why Chosen** | Required by pdf2image for high-quality PDF-to-image conversion at specified DPI |
| **Where Used** | Called by pdf2image in `app.py` `_ocr_pdf()` (line 317) |
| **Criticality** | **High** — Required for PDF OCR fallback. Without it, pdf2image cannot convert PDF pages to images |
| **Installation** | Must be installed separately. Download from poppler releases. Path hardcoded in `app.py` line 256 |
| **Alternatives** | PyMuPDF can render pages to pixmaps (used in `app_backup.py`), Ghostscript (alternative renderer) |
| **Removal Impact** | PDF OCR fallback fails. The application would only work with digital-text PDFs |

---

## Python Standard Library Dependencies

### 1. `hashlib`

| Aspect | Detail |
|--------|--------|
| **Purpose** | SHA-256 hash generation for certificate hashing and blockchain block hashing |
| **Where Used** | `app.py` (lines 3, 779) — `generate_hash()`; `blockchain.py` (lines 9, 66) — `Block._calculate_hash()`; `models/hash_utils.py` (line 1) — `generate_hash()`; `utils/cert_hash.py` (line 8) — `generate_cert_hash()` |
| **Criticality** | **Critical** — Without hashlib, certificate hashes cannot be generated, and the blockchain cannot function |
| **Removal Impact** | Complete system failure. Hash generation, blockchain storage, and verification all depend on SHA-256 |

### 2. `json`

| Aspect | Detail |
|--------|--------|
| **Purpose** | JSON serialization/deserialization for blockchain persistence and configuration files |
| **Where Used** | `blockchain.py` (lines 9, 56, 143, 181-182, 194, 207-208) — chain loading and saving; `models/certificate_store.py` (lines 1, 9, 13) — KV store |
| **Criticality** | **High** — Required for blockchain persistence. Without it, the blockchain cannot be saved or loaded |
| **Removal Impact** | Blockchain persistence fails. The `blockchain.py` module cannot function |

### 3. `os`

| Aspect | Detail |
|--------|--------|
| **Purpose** | File system operations: directory creation, file path manipulation, file existence checks |
| **Where Used** | Every module — `app.py`, `blockchain.py`, `models/`, `routes/`, `utils/` |
| **Criticality** | **Critical** — Required for file operations throughout the application |
| **Removal Impact** | Complete system failure. File saving, loading, and path manipulation would be impossible |

### 4. `re` (regular expressions)

| Aspect | Detail |
|--------|--------|
| **Purpose** | Pattern matching for field extraction, text cleaning, and validation |
| **Where Used** | `app.py` (lines 5, 258-284, 400-716) — all extraction functions, advanced_clean; `models/ocr.py` (line 8) — all extraction functions; `config/extraction_patterns.py` — pattern definitions |
| **Criticality** | **Critical** — Without regex, field extraction cannot function. The entire extraction pipeline depends on pattern matching |
| **Removal Impact** | All field extraction fails. Names, courses, dates, certificate IDs, and universities cannot be extracted from OCR text |

### 5. `logging`

| Aspect | Detail |
|--------|--------|
| **Purpose** | Application logging for debugging, error tracking, and audit trail |
| **Where Used** | `app.py` (lines 4, 18-22, 69, 127, 213, 227, 238, 302, 347, 355, 385-390, 746-755, 780, 911, 927) — extensive logging throughout |
| **Criticality** | **Medium** — Logging is not critical for functionality but is essential for debugging and monitoring |
| **Removal Impact** | No logging output. Debugging becomes significantly harder |

### 6. `copy`

| Aspect | Detail |
|--------|--------|
| **Purpose** | Deep copy operations for blockchain data immutability |
| **Where Used** | `blockchain.py` (lines 8, 46, 72) — `Block.__init__()` and `Block.to_dict()` |
| **Criticality** | **Low** — Used for data immutability, but alternative approaches exist |
| **Removal Impact** | Blockchain data could be mutated externally, potentially causing integrity issues |

### 7. `datetime`

| Aspect | Detail |
|--------|--------|
| **Purpose** | Timestamp generation for blockchain blocks |
| **Where Used** | `blockchain.py` (lines 12, 186, 237) — genesis block creation and block timestamping |
| **Criticality** | **Low** — Used for block timestamps. Alternative timestamp formats could be used |
| **Removal Impact** | Blockchain blocks would have no timestamps, reducing audit capability |

### 8. `typing`

| Aspect | Detail |
|--------|--------|
| **Purpose** | Type hints for code documentation and IDE support |
| **Where Used** | `blockchain.py` (lines 13, 69, 78, 105) — `List`, `Dict`, `Any`, `Optional`; `config/extraction_patterns.py` (line 9) — `List`, `Dict`, `Any` |
| **Criticality** | **Low** — Type hints are optional in Python. They improve code quality but are not required for execution |
| **Removal Impact** | No functional impact. Type hints can be removed without affecting runtime behavior |

---

## Development Tool Dependencies

### 1. Graphify

| Aspect | Detail |
|--------|--------|
| **Purpose** | Generates a knowledge graph from the codebase for AI-assisted navigation |
| **Where Used** | `.agents/rules/graphify.md`, `.agents/workflows/graphify.md`, `graphify-out/` directory |
| **Criticality** | **None** — Development tool only. Not required for application runtime |
| **Removal Impact** | None. The `graphify-out/` directory and `.agents/` files can be deleted without affecting the application |

---

## Dependency Graph (Runtime)

```
app.py
├── flask (external)
├── hashlib (stdlib)
├── logging (stdlib)
├── re (stdlib)
├── os (stdlib)
├── cv2 (external) ──→ numpy (external)
├── pytesseract (external) ──→ Tesseract OCR (system)
├── PIL (external)
├── pdf2image (external) ──→ Poppler (system)
├── fitz (external)
└── werkzeug (external, Flask dependency)

blockchain.py
├── copy (stdlib)
├── hashlib (stdlib)
├── json (stdlib)
├── os (stdlib)
├── datetime (stdlib)
└── typing (stdlib)

models/ocr.py
├── re (stdlib)
├── pytesseract (external) ──→ Tesseract OCR (system)
├── PIL (external)
├── pdf2image (external) ──→ Poppler (system)
└── config.extraction_patterns (internal)

models/hash_utils.py
├── hashlib (stdlib)
└── re (stdlib)

models/certificate_store.py
├── json (stdlib)
└── os (stdlib)

utils/cert_hash.py
├── hashlib (stdlib)
└── re (stdlib)
```

---

## Dependency Criticality Matrix

| Dependency | Criticality | Type | Runtime | Test | Dev |
|-----------|-------------|------|---------|------|-----|
| Flask | Critical | Python | ✓ | ✓ | ✗ |
| pytesseract | Critical | Python | ✓ | ✓ | ✗ |
| hashlib | Critical | Stdlib | ✓ | ✓ | ✗ |
| re | Critical | Stdlib | ✓ | ✓ | ✗ |
| os | Critical | Stdlib | ✓ | ✓ | ✗ |
| OpenCV | High | Python | ✓ | ✓ | ✗ |
| NumPy | High | Python | ✓ | ✓ | ✗ |
| Pillow | High | Python | ✓ | ✓ | ✗ |
| pdf2image | High | Python | ✓ | ✓ | ✗ |
| PyMuPDF | High | Python | ✓ | ✓ | ✗ |
| json | High | Stdlib | ✓ | ✓ | ✗ |
| Tesseract OCR | Critical | System | ✓ | ✓ | ✗ |
| Poppler | High | System | ✓ | ✓ | ✗ |
| python-docx | Low | Python | ✓ | ✓ | ✗ |
| textract | Low | Python | ✓ | ✓ | ✗ |
| logging | Medium | Stdlib | ✓ | ✓ | ✗ |
| copy | Low | Stdlib | ✓ | ✓ | ✗ |
| datetime | Low | Stdlib | ✓ | ✓ | ✗ |
| typing | Low | Stdlib | ✓ | ✓ | ✗ |
| Graphify | None | Dev | ✗ | ✗ | ✓ |

---

## Dependency Installation

### Required Packages

```bash
# Core dependencies
pip install Flask>=2.0
pip install Pillow>=9.0
pip install pytesseract>=0.3.10
pip install pdf2image>=1.16

# Additional dependencies (not listed in requirements.txt)
pip install opencv-python
pip install numpy
pip install PyMuPDF
pip install python-docx
pip install textract
```

### System Requirements

**Tesseract OCR:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Required languages: English (eng) by default

**Poppler (Windows):**
- Download from: https://github.com/oschwartz10612/poppler-windows/releases
- Path configuration: Hardcoded in `app.py` line 256
- Alternative: Set `POPPLER_PATH` environment variable (for `models/ocr.py`)

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview and technology stack |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference |
| [06_CONFIGURATION.md](06_CONFIGURATION.md) | Configuration details |