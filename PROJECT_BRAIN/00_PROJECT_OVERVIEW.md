# 00 — PROJECT OVERVIEW

## Project Name

**CertiChain** — Smart Certificate Authentication System

## Problem Statement

Educational institutions, training providers, and professional organizations issue millions of certificates every year. These paper-based and digital certificates are easily forged, modified, or misrepresented. There is no standardized, decentralized mechanism to verify the authenticity of a certificate without contacting the issuing organization directly. Manual verification is slow, costly, and does not scale.

## Business Objective

To build a web-based system that allows organizations to **issue** digital certificates with a tamper-proof cryptographic hash stored in a blockchain-backed ledger, and to enable any third party to **verify** the authenticity of a certificate by comparing its hash against the ledger. The system should accommodate certificates of varying layouts and formats without requiring manual configuration for each institution.

## Goals

1. **Certificate Issuance**: Allow an authorized user (administrator) to upload a certificate document (PDF, image, DOC/DOCX) and have it automatically processed, hashed, and added to the blockchain.
2. **Certificate Verification**: Allow any user to upload a certificate document and determine whether it is authentic (hash exists in the blockchain) or fake (hash not found).
3. **Automated OCR-based Extraction**: Automatically extract key fields (recipient name, course name, issue date, certificate ID, issuing organization) from uploaded certificate images/PDFs using Optical Character Recognition (OCR).
4. **Tamper-Proof Storage**: Store certificate hashes in a blockchain structure with linked blocks, ensuring that any tampering with the stored data is detectable.
5. **Pattern-based Flexibility**: Support certificate layouts from different institutions without hardcoding institution-specific text by using configurable extraction patterns.

## Current Capabilities

- **Web UI** (Flask-based): Home page, Issue page, Verify page, Result page with a modern dark-themed UI using Tailwind CSS.
- **REST API**: `/api/issue` and `/api/verify` endpoints for programmatic access.
- **Multi-format OCR**: Supports PDF, PNG, JPG, JPEG, DOCX, DOC file uploads.
- **Advanced Image Preprocessing**: Grayscale conversion, Gaussian blur, Non-Local Means denoising, deskew (rotation correction), Otsu binarization, upscaling for small images.
- **Multi-PSM OCR**: Tesseract OCR runs with multiple Page Segmentation Modes (PSM 3, 4, 6) and selects the best result.
- **PDF Pipeline**: Two-stage extraction — first attempts digital text extraction via PyMuPDF, then falls back to high-DPI (450 DPI) OCR if insufficient digital text is found.
- **Layout-based Name Detection**: Uses OCR coordinate data to detect the largest centered text block as the recipient name.
- **Pattern-based Field Extraction**: Configurable pattern lists for name, course, date, certificate ID, and university extraction in `config/extraction_patterns.py`.
- **Canonical Hashing**: Normalized field values (whitespace-collapsed, stripped) ensure consistent hash generation across issue and verify operations.
- **Blockchain Persistence**: Chain stored in `blockchain.json` with block structure (index, timestamp, data, previous_hash, hash).
- **Chain Validation**: `validate_chain()` verifies genesis block, hash integrity, and previous_hash linkage on every load.
- **Legacy Migration**: Automatic migration from legacy `issue_certificate.json` format to the new blockchain format.
- **Duplicate Detection**: Prevents adding duplicate certificate hashes to the blockchain.
- **Graceful Degradation**: Multiple fallback strategies for field extraction.

## Future Vision

- Digital signature support for certificates
- QR code generation and verification
- Admin authentication and role-based access control
- User management dashboard
- Bulk certificate issuance
- Public verification API
- Integration with institutional student information systems
- Mobile application for scanning and verification
- Decentralized storage (IPFS) for certificate images
- Multi-blockchain support (Ethereum, Hyperledger)
- Certificate revocation capability
- Email-based certificate delivery
- Analytics dashboard for issuance and verification statistics

## Technology Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | Flask | >=2.0 |
| Language | Python | 3.13 |
| OCR Engine | Tesseract (via pytesseract) | 0.3.10+ |
| Image Processing | OpenCV (cv2) | Latest |
| Image Processing | Pillow (PIL) | >=9.0 |
| PDF Processing | PyMuPDF (fitz) | Latest |
| PDF-to-Image | pdf2image | >=1.16 |
| Numeric | NumPy | Latest |
| DOCX Processing | python-docx | Latest |
| DOC Processing | textract | Latest |

### Frontend
| Component | Technology |
|-----------|-----------|
| Templating | Jinja2 (Flask) |
| CSS Framework | Tailwind CSS v4 |
| CSS | Custom CSS (style.css, animations.css, main.css) |
| JavaScript | Vanilla JS (loader, fade-in) |
| UI Components | Custom shadcn-style components |
| Font | Inter (Google Fonts) |

### Storage
| Component | Technology |
|-----------|-----------|
| Blockchain Storage | JSON file (`blockchain.json`) |
| Legacy Storage | JSON file (`issue_certificate.json`) |
| Legacy KV Store | JSON file (`db.json` via `models/certificate_store.py`) |
| File Uploads | Filesystem (`uploads/` directory) |

### External Tools
| Tool | Purpose |
|------|---------|
| Tesseract OCR | Text extraction from images |
| Poppler | PDF rendering (for pdf2image) |
| Graphify | Knowledge graph generation (development tool) |

## Project Philosophy

1. **Pattern over hardcoding**: All extraction logic uses configurable patterns, not institution-specific text strings. Adding support for a new certificate layout means adding patterns, not changing code.
2. **Canonical representation**: Hashing uses normalized field values to ensure that minor OCR variations (extra spaces, case differences) do not cause verification failures.
3. **Defense in depth**: Multiple extraction strategies (label-based, trigger-phrase, regex, layout-based) ensure robustness. Each field extraction has fallback mechanisms.
4. **Blockchain integrity**: The blockchain structure enforces immutability — each block references the previous block's hash, and the entire chain is validated on load.
5. **Graceful degradation**: OCR failures, extraction failures, and blockchain corruption are handled gracefully with meaningful fallbacks.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER / CLIENT                                │
│                (Browser / API Client / cURL)                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTP
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       FLASK WEB SERVER  (app.py)                      │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐               │
│  │  Web Routes  │  │  API Routes  │  │  Static Files │               │
│  │  GET /       │  │  POST /api/  │  │  CSS / JS     │               │
│  │  GET/POST /issue │  issue      │  │  Templates    │               │
│  │  GET/POST /verify │  POST /api/│  │               │               │
│  │             │  │  verify       │  │               │               │
│  └──────┬──────┘  └──────┬───────┘  └───────────────┘               │
│         │                │                                          │
└─────────┼────────────────┼──────────────────────────────────────────┘
          │                │
          ▼                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        OCR PIPELINE                                   │
│                                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────┐  │
│  │ File I/O │  │  Image Pre-  │  │  OCR Engine   │  │  Text      │  │
│  │ Upload   │─▶│  processing  │─▶│  (Tesseract)  │─▶│  Cleaning  │  │
│  │ Save     │  │  Deskew      │  │  Multi-PSM    │  │  Advanced  │  │
│  │          │  │  Denoise     │  │  Multi-Page   │  │  Cleaner   │  │
│  └──────────┘  └──────────────┘  └───────────────┘  └────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    FIELD EXTRACTION PIPELINE                          │
│                                                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ Name       │  │ Course     │  │ Date       │  │ Certificate   │  │
│  │ Extraction │  │ Extraction │  │ Extraction │  │ ID Extraction │  │
│  │ (Label/    │  │ (Trigger/  │  │ (Label/    │  │ (Label/Regex/ │  │
│  │ Trigger/   │  │ Label/     │  │ Regex)     │  │ URL)          │  │
│  │ Layout)    │  │ Degree)    │  │            │  │               │  │
│  └────────────┘  └────────────┘  └────────────┘  └───────────────┘  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐                                  │
│  │ University   │  │ Year         │                                  │
│  │ Extraction   │  │ Extraction   │                                  │
│  └──────────────┘  └──────────────┘                                  │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      HASH GENERATION                                  │
│                                                                      │
│  SHA-256( name | course | date | cert_id )                           │
│  Canonical: normalized whitespace, lowercased non-name fields        │
└──────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      BLOCKCHAIN LAYER                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Blockchain (chain of Blocks)                                 │    │
│  │  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐                  │    │
│  │  │Genesis│──│Block 1│──│Block 2│──│Block 3│── ...             │    │
│  │  │Index 0│  │Index 1│  │Index 2│  │Index 3│                  │    │
│  │  │Hash:  │  │Data:  │  │Data:  │  │Data:  │                  │    │
│  │  │abc... │  │cert...│  │cert...│  │cert...│                  │    │
│  │  │Prev: 0│  │Prev:  │  │Prev:  │  │Prev:  │                  │    │
│  │  │       │  │abc... │  │def... │  │ghi... │                  │    │
│  │  └───────┘  └───────┘  └───────┘  └───────┘                  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                               │                                       │
│                               ▼                                       │
│                    ┌─────────────────────┐                            │
│                    │   blockchain.json    │                            │
│                    │   (persistence)      │                            │
│                    └─────────────────────┘                            │
└──────────────────────────────────────────────────────────────────────┘
```

## Repository Summary

| Aspect | Detail |
|--------|--------|
| Total Source Files (Python) | ~12 files |
| Total Templates | 5 HTML files |
| Total CSS Files | 4 files |
| Total JS Files | 2 files |
| Total JSON Files | 3 (blockchain.json, issue_certificate.json, db.json) |
| Lines of Python Code | ~1,800+ |
| Lines of HTML/CSS/JS | ~1,500+ |
| Test Coverage | Minimal (1 test script: test_ocr.py) |
| Documentation | ARCHITECTURE.md, README.md |

## Key Architectural Decisions

1. **Monolithic Flask app** (`app.py`) contains all routes, OCR logic, field extraction, and blockchain operations. This is the primary deployment artifact.
2. **Modular refactored code** exists in parallel (routes/, models/, utils/, config/) but is **not fully integrated** — the main `app.py` does not import from these modules.
3. **Blockchain is file-based**, not a real distributed ledger. It uses JSON file persistence with linked hashes.
4. **OCR preprocessing is aggressive** — upscaling, denoising, deskewing, and binarization are applied to maximize Tesseract accuracy.
5. **Pattern-based extraction** is configurable via `config/extraction_patterns.py` with no hardcoded certificate wording.
6. **Two concurrent hashing systems** exist: one in `app.py` (simple text-based) and one in `utils/cert_hash.py` (canonical normalized). The app.py version is the one actively used by routes.

## Related Documents

| Document | Description |
|----------|-------------|
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | Detailed system architecture, module relationships, and execution flows |
| [02_DIRECTORY_STRUCTURE.md](02_DIRECTORY_STRUCTURE.md) | Complete directory tree and folder responsibilities |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference: classes, functions, imports, dependencies |
| [04_PIPELINES.md](04_PIPELINES.md) | Detailed pipeline documentation with sequence diagrams |
| [05_API_REFERENCE.md](05_API_REFERENCE.md) | Flask endpoint documentation |
| [06_CONFIGURATION.md](06_CONFIGURATION.md) | Configuration files, paths, constants |
| [07_DEPENDENCIES.md](07_DEPENDENCIES.md) | Dependency analysis |
| [08_DATA_STORAGE.md](08_DATA_STORAGE.md) | Storage mechanisms and data formats |
| [09_SECURITY_REVIEW.md](09_SECURITY_REVIEW.md) | Security analysis |
| [10_DESIGN_DECISIONS.md](10_DESIGN_DECISIONS.md) | Architectural decisions and rationale |
| [11_CURRENT_STATUS.md](11_CURRENT_STATUS.md) | Current project status, known issues, tech debt |
| [12_TODO_ROADMAP.md](12_TODO_ROADMAP.md) | Prioritized roadmap |
| [13_AI_GUIDELINES.md](13_AI_GUIDELINES.md) | Engineering rules for AI coding agents |
| [14_GLOSSARY.md](14_GLOSSARY.md) | Key concepts and terminology |
| [15_PROJECT_EVOLUTION_HISTORY.md](15_PROJECT_EVOLUTION_HISTORY.md) | Chronological evolution and historical context |
