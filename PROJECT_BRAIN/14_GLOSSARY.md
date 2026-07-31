# 14 — GLOSSARY

## Overview

This document defines every important concept used throughout the Certificate Authentication System project. Each entry includes a definition, context, and cross-references to relevant documentation.

---

## A

### Advanced Cleaning
**Definition:** A multi-stage text cleaning process applied to PDF OCR output that removes non-printable characters, isolated symbols, page number artifacts, and normalizes whitespace.
**See also:** Text Cleaning, OCR Pipeline
**Source:** `app.py` `advanced_clean()` function, lines 258-284

### Allowed Extensions
**Definition:** The set of file extensions that the application accepts for upload: `pdf`, `png`, `jpg`, `jpeg`, `doc`, `docx`.
**See also:** `allowed_file()` function
**Source:** `app.py` line 31

### API Endpoint
**Definition:** A JSON-based HTTP endpoint for programmatic access to certificate issuance and verification. Two endpoints exist: `POST /api/issue` and `POST /api/verify`.
**See also:** Certificate Issue, Certificate Verification
**Source:** `app.py` lines 899-928

---

## B

### Block
**Definition:** A single unit in the blockchain. Each block contains an index, timestamp, data payload, previous block hash, and its own hash.
**See also:** Blockchain, Genesis Block
**Source:** `blockchain.py` `Block` class, lines 33-85

### Blockchain
**Definition:** A chain of blocks where each block references the previous block's hash, creating a tamper-evident ledger. The project has two implementations: a simple text-based one in `app.py` and a full structured one in `blockchain.py`.
**See also:** Block, Genesis Block, Chain Validation
**Source:** `app.py` lines 784-802, `blockchain.py` lines 99-250

### Blockchain.txt
**Definition:** Plain text file used by `app.py` as a simple blockchain storage. Contains one SHA-256 hash per line.
**See also:** Blockchain, blockchain.json
**Source:** `app.py` line 27, lines 784-797

### Blockchain.json
**Definition:** JSON file used by `blockchain.py` for structured blockchain persistence. Contains a chain of blocks with index, timestamp, data, previous_hash, and hash.
**See also:** Blockchain, Block
**Source:** `blockchain.py` lines 19-22

---

## C

### Candidate
**Definition:** A user who has been issued a certificate. In the context of the system, the term "candidate" is used as a label keyword for name extraction (e.g., "Candidate Name").
**See also:** Name Extraction
**Source:** `config/extraction_patterns.py` line 86

### Canonical Hash
**Definition:** A SHA-256 hash generated from normalized certificate fields. Normalization (whitespace collapse, lowercase for non-name fields) ensures consistent hashing across OCR variations.
**See also:** Hash Generation, Normalization
**Source:** `utils/cert_hash.py` `generate_cert_hash()` function, lines 39-48

### Certificate
**Definition:** A document issued by an educational institution, training provider, or professional organization that certifies the recipient has completed a course, program, or achieved a qualification. The system processes certificates in PDF, PNG, JPG, JPEG, DOCX, and DOC formats.

### Certificate ID
**Definition:** A unique identifier for a certificate, typically alphanumeric. Extracted from the certificate text using label patterns, regex patterns, or URL patterns. If not found, a synthetic ID is generated: `"CERT-" + first 9 characters of hash, uppercased`.
**See also:** Certificate ID Extraction, Synthetic Cert ID
**Source:** `app.py` lines 606-652, 886-888

### Certificate Issue
**Definition:** The process of uploading a certificate, extracting its text via OCR, parsing structured fields, generating a hash, and storing the hash in the blockchain. The result is a tamper-proof record of the certificate's existence.
**See also:** Certificate Verification, OCR Pipeline, Field Extraction
**Source:** `app.py` `issue()` function, lines 813-839

### Certificate Verification
**Definition:** The process of uploading a certificate, extracting its text via OCR, parsing structured fields, generating a hash, and checking if the hash exists in the blockchain. Returns "VERIFIED" if found, "FAKE" if not.
**See also:** Certificate Issue, Blockchain Verification
**Source:** `app.py` `verify()` function, lines 842-864

### Chain Validation
**Definition:** The process of verifying the integrity of a blockchain by checking that the genesis block is valid, each block's hash matches its content, and each block's `previous_hash` matches the previous block's hash.
**See also:** Blockchain, Block
**Source:** `blockchain.py` `validate_chain()` method, lines 210-228

### CSRF (Cross-Site Request Forgery)
**Definition:** A security vulnerability where an attacker tricks a user's browser into making unwanted requests to a web application. The application currently has no CSRF protection.
**See also:** Security Review
**Source:** `09_SECURITY_REVIEW.md` Section 9

---

## D

### Deskew
**Definition:** The process of correcting rotational skew in scanned documents. The `_deskew()` function uses OpenCV's `minAreaRect` on dark pixel coordinates to estimate the rotation angle and applies an affine transformation to correct it.
**See also:** Image Preprocessing
**Source:** `app.py` `_deskew()` function, lines 50-70

### Digital Text Extraction
**Definition:** The first stage of PDF text extraction, using PyMuPDF (fitz) to extract text blocks directly from the PDF's internal text layer. This is fast and accurate for born-digital PDFs.
**See also:** PDF Extraction, OCR Fallback
**Source:** `app.py` `_ocr_pdf()` Stage 1, lines 286-310

---

## E

### Extraction
**Definition:** The process of parsing raw OCR text to extract structured certificate fields: name, course, date, certificate ID, university, and year.
**See also:** Field Extraction, Name Extraction, Course Extraction, Date Extraction, Certificate ID Extraction, University Extraction, Year Extraction
**Source:** `app.py` `extract_details()` function, lines 722-765

---

## F

### FAKE
**Definition:** The verification status returned when a certificate's hash is not found in the blockchain. Indicates the certificate was not previously issued through the system or has been tampered with.
**See also:** VERIFIED, Certificate Verification
**Source:** `app.py` `verify_certificate()` function, line 802

### Field Extraction
**Definition:** The process of extracting structured fields (name, course, date, cert_id, university, year) from raw OCR text using multiple strategies with fallbacks.
**See also:** Name Extraction, Course Extraction, Date Extraction, Certificate ID Extraction, University Extraction, Year Extraction
**Source:** `app.py` `extract_details()` function, lines 722-765

---

## G

### Genesis Block
**Definition:** The first block in the blockchain (index 0) with data "Genesis Block" and `previous_hash = "0"`. It is the foundation of the chain and is created automatically when the blockchain is initialized for the first time.
**See also:** Block, Blockchain
**Source:** `blockchain.py` `_create_genesis_block()` method, lines 184-189

### Graphify
**Definition:** A development tool that generates a knowledge graph from the codebase for AI-assisted navigation. The output is stored in the `graphify-out/` directory.
**See also:** Knowledge Graph
**Source:** `.agents/rules/graphify.md`, `.agents/workflows/graphify.md`

---

## H

### Hash Generation
**Definition:** The process of creating a SHA-256 hash from the extracted certificate fields. The `app.py` version concatenates 5 fields with pipe separators. The `utils/cert_hash.py` version normalizes fields first.
**See also:** Canonical Hash, SHA-256, Normalization
**Source:** `app.py` `generate_hash()` function, lines 771-781; `utils/cert_hash.py` `generate_cert_hash()` function, lines 39-48

---

## I

### Image Preprocessing
**Definition:** A 6-stage image processing pipeline applied before OCR to maximize text recognition accuracy: upscaling, grayscale conversion, Gaussian blur, Non-Local Means denoising, deskew (rotation correction), and Otsu binarization.
**See also:** OCR Pipeline, Deskew, Otsu Binarization
**Source:** `app.py` `_preprocess_for_ocr()` function, lines 73-109

### Issuer
**Definition:** The organization or institution that issues the certificate. Also referred to as the "university" in the extraction pipeline. Extracted using keyword scoring of the certificate text.
**See also:** University Extraction
**Source:** `app.py` `_extract_university()` function, lines 655-707

---

## K

### Knowledge Graph
**Definition:** A structured representation of the codebase generated by the Graphify tool, stored in `graphify-out/`. Used by AI agents for codebase navigation and understanding.
**See also:** Graphify
**Source:** `graphify-out/` directory

---

## L

### Label-Based Extraction
**Definition:** A field extraction strategy that searches for patterns like "Label: value" in the certificate text. For example, "Name: John Doe" or "Date of Issue: 01/15/2024".
**See also:** Field Extraction, Name Extraction, Course Extraction, Date Extraction, Certificate ID Extraction
**Source:** `app.py` `_label_extract()` function, lines 416-437

### Legacy Migration
**Definition:** The automatic process of converting certificate data from the old `issue_certificate.json` format to the new `blockchain.json` blockchain format. Occurs when `blockchain.json` does not exist but `issue_certificate.json` does.
**See also:** Blockchain, issue_certificate.json
**Source:** `blockchain.py` `_load_legacy()` method, lines 140-172

### Ledger
**Definition:** A record of certificate transactions. In this system, the ledger is the blockchain — a chain of blocks where each block represents a certificate issuance event.
**See also:** Blockchain

---

## N

### Name Extraction
**Definition:** The process of extracting the recipient's name from the certificate text using three strategies with fallback: label-based (e.g., "Name: John Doe"), trigger phrase (e.g., "This is to certify that John Doe"), and fallback heuristic (short capitalized lines).
**See also:** Field Extraction, Label-Based Extraction, Trigger Phrase Extraction
**Source:** `app.py` `_extract_name()` function, lines 443-507

### Non-Local Means Denoising
**Definition:** An image denoising technique that preserves edges while removing noise by averaging pixels based on their similarity to a target pixel, not just spatial proximity.
**See also:** Image Preprocessing
**Source:** `app.py` line 102

### Normalization
**Definition:** The process of standardizing certificate field values before hashing to ensure consistency across OCR variations. Includes collapsing whitespace and optionally lowercasing. Currently only implemented in `utils/cert_hash.py`, not in `app.py`.
**See also:** Canonical Hash, Hash Generation
**Source:** `utils/cert_hash.py` `_normalize_field()` function, lines 12-16

### Not Provided
**Definition:** The default placeholder value used when a certificate field cannot be extracted from the OCR text. Defined as a constant in `app.py`.
**See also:** Field Extraction
**Source:** `app.py` line 397

---

## O

### OCR (Optical Character Recognition)
**Definition:** The technology used to extract text from images and scanned documents. The system uses Tesseract OCR via the pytesseract Python wrapper.
**See also:** OCR Pipeline, Tesseract, pytesseract
**Source:** `app.py` `perform_ocr()` function, lines 369-391

### OCR Fallback
**Definition:** The second stage of PDF text extraction, activated when digital text extraction yields less than 200 characters. Converts PDF pages to high-resolution images (450 DPI) and applies the full image preprocessing + OCR pipeline.
**See also:** PDF Extraction, Digital Text Extraction
**Source:** `app.py` `_ocr_pdf()` Stage 2, lines 313-356

### OCR Pipeline
**Definition:** The complete text extraction pipeline that routes files to the appropriate handler based on file extension and applies preprocessing, OCR, and cleaning.
**See also:** OCR, Image Preprocessing, PDF Extraction, Text Cleaning
**Source:** `app.py` `perform_ocr()` function, lines 369-391

### Otsu Binarization
**Definition:** An automatic thresholding technique that converts a grayscale image to pure black and white. OpenCV's `THRESH_OTSU` flag automatically determines the optimal threshold value.
**See also:** Image Preprocessing
**Source:** `app.py` line 108

---

## P

### Pattern-Based Extraction
**Definition:** A design philosophy where all extraction patterns are defined in configurable lists (in `config/extraction_patterns.py`), allowing new certificate layouts to be supported by adding patterns rather than changing code.
**See also:** config/extraction_patterns.py, Field Extraction
**Source:** `config/extraction_patterns.py`

### PDF Extraction
**Definition:** A two-stage text extraction process for PDF files: first attempt digital text extraction via PyMuPDF, then fall back to high-DPI OCR if insufficient text is found.
**See also:** Digital Text Extraction, OCR Fallback
**Source:** `app.py` `_ocr_pdf()` function, lines 242-366

### Poppler
**Definition:** An external system tool required by `pdf2image` for converting PDF pages to images. The path is hardcoded in `app.py` for Windows.
**See also:** pdf2image, OCR Fallback
**Source:** `app.py` line 256

### PSM (Page Segmentation Mode)
**Definition:** A Tesseract configuration parameter that tells the OCR engine how to analyze the page layout. The system uses three modes: PSM 3 (automatic), PSM 4 (single column), and PSM 6 (uniform block).
**See also:** Tesseract, OCR
**Source:** `app.py` lines 118-121, 331-332

### pytesseract
**Definition:** The Python wrapper for the Tesseract OCR engine. Provides the `image_to_string()` function that extracts text from images.
**See also:** Tesseract, OCR
**Source:** `app.py` line 8

---

## S

### SHA-256
**Definition:** A cryptographic hash function that produces a 256-bit (64-character hexadecimal) hash. Used for certificate hashing and blockchain block hashing.
**See also:** Hash Generation, Canonical Hash
**Source:** `app.py` line 779, `blockchain.py` line 66

### Synthetic Cert ID
**Definition:** An auto-generated certificate identifier created when the certificate ID cannot be extracted from the text. Format: `"CERT-" + first 9 characters of the hash, uppercased`.
**See also:** Certificate ID, API Response
**Source:** `app.py` `_details_to_api()` function, line 888

---

## T

### Tesseract
**Definition:** The open-source OCR engine used by the system. It is called via the pytesseract Python wrapper. Must be installed separately on the system.
**See also:** pytesseract, OCR
**Source:** External dependency

### Text Cleaning
**Definition:** The process of removing non-printable characters, isolated symbols, page number artifacts, and normalizing whitespace in OCR output. Currently only applied to PDF extraction output.
**See also:** Advanced Cleaning, OCR Pipeline
**Source:** `app.py` `advanced_clean()` function, lines 258-284

### Trigger Phrase Extraction
**Definition:** A field extraction strategy that uses common certificate phrases (e.g., "This is to certify that", "successfully completed") to locate the subsequent value on the same or next line.
**See also:** Name Extraction, Course Extraction, Field Extraction
**Source:** `app.py` `_extract_name()` function, lines 457-491; `_extract_course()` function, lines 545-561

---

## U

### University Extraction
**Definition:** The process of extracting the issuing organization name using keyword scoring. University keywords (university, institute, college) score +5, organization keywords (devtown, coursera, google) score +6, and length bonus adds +2.
**See also:** Field Extraction, Issuer
**Source:** `app.py` `_extract_university()` function, lines 655-707

### Unknown
**Definition:** The default value used for missing or unextractable fields in the extraction pipeline. Used consistently throughout the system. Also used as a category in design decisions documentation for items that cannot be determined from repository inspection.
**See also:** Not Provided, Field Extraction
**Source:** `app.py` `extract_details()` function, line 735

---

## V

### VERIFIED
**Definition:** The verification status returned when a certificate's hash is found in the blockchain. Confirms the certificate was previously issued through the system.
**See also:** FAKE, Certificate Verification
**Source:** `app.py` `verify_certificate()` function, line 802

---

## W

### Werkzeug
**Definition:** The WSGI toolkit used by Flask. Provides `secure_filename()` for file sanitization and the development server with debugger.
**See also:** Flask, secure_filename
**Source:** `app.py` line 12

---

## Y

### Year Extraction
**Definition:** The process of extracting the year from the certificate text using regex. Captures all 4-digit numbers starting with 19 or 20 and returns the maximum (most recent) year.
**See also:** Field Extraction
**Source:** `app.py` `_extract_year()` function, lines 709-716

---

## Index

| Term | Category | Document Reference |
|------|----------|-------------------|
| Advanced Cleaning | Pipeline | 04_PIPELINES.md |
| Block | Blockchain | 03_FILE_REFERENCE.md (blockchain.py) |
| Blockchain | Storage | 08_DATA_STORAGE.md |
| Canonical Hash | Hashing | 03_FILE_REFERENCE.md (utils/cert_hash.py) |
| Certificate Issue | Workflow | 04_PIPELINES.md (Pipeline 2) |
| Certificate Verification | Workflow | 04_PIPELINES.md (Pipeline 3) |
| Chain Validation | Blockchain | 04_PIPELINES.md (blockchain.py) |
| CSRF | Security | 09_SECURITY_REVIEW.md |
| Deskew | Image Processing | 04_PIPELINES.md (Pipeline 9) |
| FAKE | Status | 05_API_REFERENCE.md |
| Field Extraction | Pipeline | 04_PIPELINES.md (Pipeline 10) |
| Genesis Block | Blockchain | 03_FILE_REFERENCE.md (blockchain.py) |
| Hash Generation | Pipeline | 04_PIPELINES.md (Pipeline 17) |
| Image Preprocessing | Pipeline | 04_PIPELINES.md (Pipeline 9) |
| Label-Based Extraction | Strategy | 04_PIPELINES.md (Pipeline 10) |
| Name Extraction | Pipeline | 04_PIPELINES.md (Pipeline 11) |
| OCR | Pipeline | 04_PIPELINES.md (Pipeline 6) |
| Otsu Binarization | Image Processing | 04_PIPELINES.md (Pipeline 9) |
| PDF Extraction | Pipeline | 04_PIPELINES.md (Pipeline 7) |
| PSM | OCR | 04_PIPELINES.md (Pipeline 7) |
| SHA-256 | Cryptography | 04_PIPELINES.md (Pipeline 17) |
| Tesseract | System Tool | 07_DEPENDENCIES.md |
| Trigger Phrase Extraction | Strategy | 04_PIPELINES.md (Pipeline 11) |
| VERIFIED | Status | 05_API_REFERENCE.md |

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference |
| [04_PIPELINES.md](04_PIPELINES.md) | Pipeline documentation |