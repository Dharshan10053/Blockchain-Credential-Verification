# 06 — CONFIGURATION

## Overview

This document documents all configuration mechanisms in the Certificate Authentication System, including configuration files, runtime constants, environment variables, file paths, and startup behavior.

---

## Configuration Sources

| # | Source | Type | Priority | Description |
|---|--------|------|----------|-------------|
| 1 | `app.py` constants | Hardcoded | Highest | Runtime constants defined at module level |
| 2 | `config/extraction_patterns.py` | Python module | High | Extraction pattern definitions |
| 3 | `blockchain.py` constants | Hardcoded | High | Blockchain file paths and configuration |
| 4 | Environment variables | OS env | Medium | System-level configuration |
| 5 | `requirements.txt` | Text file | Low | Dependency versions |
| 6 | `blockchain.json` | JSON file | Runtime | Persisted blockchain state |
| 7 | `issue_certificate.json` | JSON file | Legacy | Legacy certificate storage |
| 8 | `blockchain.txt` | Text file | Runtime | Simple hash-based blockchain |
| 9 | `db.json` | JSON file | Legacy | Legacy KV store |
| 10 | `extraction_system.log` | Log file | Runtime | Application log output |

---

## 1. Application Constants (`app.py`)

All constants are defined at module level in `app.py` and are hardcoded with no environment variable overrides.

### File Paths

| Constant | Value | Type | Purpose | File | Line |
|----------|-------|------|---------|------|------|
| `UPLOAD_FOLDER` | `"uploads"` | `str` | Directory for uploaded certificate files | `app.py` | 26 |
| `BLOCKCHAIN_FILE` | `"blockchain.txt"` | `str` | File for simple hash-based blockchain | `app.py` | 27 |

### File Validation

| Constant | Value | Type | Purpose | File | Line |
|----------|-------|------|---------|------|------|
| `ALLOWED_EXTENSIONS` | `{"pdf", "png", "jpg", "jpeg", "doc", "docx"}` | `set` | Valid file extensions for upload | `app.py` | 31 |

### Field Extraction

| Constant | Value | Type | Purpose | File | Line |
|----------|-------|------|---------|------|------|
| `NOT_PROVIDED` | `"Not Provided"` | `str` | Placeholder for missing field values | `app.py` | 397 |

### Logging Configuration

| Parameter | Value | File | Line |
|-----------|-------|------|------|
| Level | `logging.DEBUG` | `app.py` | 18 |
| Format | `"%(asctime)s [%(levelname)s] %(message)s"` | `app.py` | 19 |
| Logger name | `__name__` (resolves to `__main__`) | `app.py` | 22 |

### Flask Configuration

| Parameter | Value | File | Line |
|-----------|-------|------|------|
| `app.debug` | `True` | `app.py` | 935 |
| Host | `127.0.0.1` (default) | `app.py` | 935 |
| Port | `5000` (default) | `app.py` | 935 |

---

## 2. Extraction Pattern Configuration (`config/extraction_patterns.py`)

This file contains all configurable extraction patterns. It is imported by `models/ocr.py` but **not** by `app.py`.

### Date Patterns

**Variable:** `DATE_PATTERNS` (line 15)
**Getter:** `get_date_patterns()` (line 24)

| Pattern | Regex | Example Match |
|---------|-------|---------------|
| 1 | `\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b` | `04/03/2026`, `12-25-2024` |
| 2 | `\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b` | `2026-03-04` |
| 3 | `\b(?:Jan|Feb|Mar|...)\s+\d{1,2},?\s+\d{4}\b` | `March 4, 2026` |
| 4 | `\b\d{1,2}\s+(?:Jan|Feb|Mar|...)\s+\d{4}\b` | `4 March 2026` |
| 5 | `\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|...)\s*,?\s*\d{4}\b` | `4th March 2026` |

### ID Patterns

**Variable:** `ID_REGEX_PATTERNS` (line 32), `ID_LABEL_KEYWORDS` (line 39)
**Getter:** `get_id_patterns()` (line 49)

| Pattern Type | Patterns |
|-------------|----------|
| Label keywords | `id`, `certificate id`, `cert id`, `ref`, `reference`, `number` |
| Regex 1 | `(?:Id|ID|Certificate\s*ID)[:\s]+([A-Za-z0-9\-_]+)` |
| Regex 2 | `(?:Cert\.?\s*#?|Ref\.?|Number)[:\s]*([A-Za-z0-9\-_]+)` |
| Regex 3 | `\b([A-Z]{2,}[0-9]{4,}[A-Za-z0-9\-]*)\b` |
| Regex 4 | `\b([A-Za-z]+\d{5,}[A-Za-z0-9\-]*)\b` |

### Name Patterns

**Variable:** `NAME_TRIGGER_PHRASES` (line 61), `NAME_LABEL_KEYWORDS` (line 82), `NAME_FALLBACK_EXCLUDE` (line 91)
**Getter:** `get_name_patterns()` (line 110)

| Pattern Group | Values |
|--------------|--------|
| Trigger phrases | `presented to`, `awarded to`, `given to`, `certified that`, `recipient`, `candidate`, `awarded`, `granted to`, `this is to certify that`, `is hereby awarded to` |
| Skip if contains | `certificate of completion`, `certificate of participation`, `certificate of achievement` |
| Label keywords | `name:`, `recipient:`, `candidate:`, `awarded to:`, `participant:` |
| Fallback exclude | `certificate`, `completion`, `course`, `training`, `founder`, `director`, `academy`, `institute`, `university`, `college`, `date`, `id`, `program`, `verified`, `issued` |
| Config | `fallback_min_line_index: 2`, `fallback_max_words: 4` |

### Course Patterns

**Variable:** `COURSE_TRIGGER_PHRASES` (line 125), `COURSE_LABEL_KEYWORDS` (line 143), `COURSE_EXCLUDE_KEYWORDS` (line 154)
**Getter:** `get_course_patterns()` (line 176)

| Pattern Group | Values |
|--------------|--------|
| Trigger phrases | `completed`, `completion of`, `successfully completed`, `for successfully completing`, `has completed`, `for completing`, `for the course`, `course entitled`, `program:`, `course:` |
| Skip if contains | `certificate of completion`, `certificate of participation` |
| Label keywords | `course:`, `program:`, `training:`, `module:`, `subject:` |
| Exclude keywords | `ceo`, `founder`, `certificate`, `id`, `date`, `director`, `signature` |
| Config | `max_words: 8`, `scan_forward_lines: 4`, `max_uppercase_ratio: 0.6`, `max_chars_with_period: 40`, `max_commas: 2` |

---

## 3. Blockchain Configuration (`blockchain.py`)

### File Paths

| Constant | Value | Type | Purpose | Line |
|----------|-------|------|---------|------|
| `BLOCKCHAIN_FILE` | `os.path.join(os.path.dirname(os.path.abspath(__file__)), "blockchain.json")` | `str` | Path to blockchain JSON file | 19-22 |
| `LEGACY_FILE` | `os.path.join(os.path.dirname(os.path.abspath(__file__)), "issue_certificate.json")` | `str` | Path to legacy certificate file | 23-26 |

**Resolution:** Both paths are resolved relative to `blockchain.py`'s location, so they point to `c:\Projects\certificateproject\blockchain.json` and `c:\Projects\certificateproject\issue_certificate.json`.

### Block Structure

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Position in chain (0 = genesis) |
| `timestamp` | `str` | ISO 8601 format with "Z" suffix (e.g., `"2026-03-03T12:12:52.018845Z"`) |
| `data` | `Any` | Certificate payload (deep-copied dict) |
| `previous_hash` | `str` | SHA-256 hash of previous block |
| `hash` | `str` | SHA-256 hash of this block |

### Hash Calculation

```python
block_string = (
    str(self.index)
    + str(self.timestamp)
    + json.dumps(self._data, sort_keys=True, separators=(",", ":"))
    + str(self.previous_hash)
)
return hashlib.sha256(block_string.encode()).hexdigest()
```

**Note:** JSON serialization uses `sort_keys=True` and `separators=(",", ":")` for deterministic output.

### Genesis Block

| Field | Value |
|-------|-------|
| `index` | `0` |
| `timestamp` | Current UTC time (ISO 8601) |
| `data` | `"Genesis Block"` |
| `previous_hash` | `"0"` |

---

## 4. Environment Variables

The application does **not** use environment variables for configuration. All paths and settings are hardcoded.

**Notable hardcoded paths that should be environment variables:**

| Path | Hardcoded In | Purpose |
|------|-------------|---------|
| `C:\poppler\Library\bin\poppler-25.12.0\Library\bin` | `app.py` line 256 | Poppler binary path for PDF processing |
| `C:\Program Files\Tesseract-OCR\tesseract.exe` | `ocr_utils.py` line 5 | Tesseract executable path |

**From `models/ocr.py` (lines 227-233):** The refactored OCR module checks `os.environ.get("POPPLER_PATH")` as a fallback:
```python
poppler = os.environ.get("POPPLER_PATH")
if poppler:
    from pdf2image import convert_from_path
    pages = convert_from_path(file_path, poppler_path=poppler)
```

This is a more portable approach than the hardcoded path in `app.py`.

---

## 5. Dependency Versions (`requirements.txt`)

**File:** `c:\Projects\certificateproject\requirements.txt`

```
Flask>=2.0
Pillow>=9.0
pytesseract>=0.3.10
pdf2image>=1.16
```

**Note:** This file is incomplete. Missing dependencies (confirmed from `app.py` imports):

| Missing Package | Import Name | Install Command |
|----------------|-------------|-----------------|
| `opencv-python` | `cv2` | `pip install opencv-python` |
| `numpy` | `numpy` | `pip install numpy` |
| `PyMuPDF` | `fitz` | `pip install PyMuPDF` |
| `python-docx` | `docx` | `pip install python-docx` |
| `textract` | `textract` | `pip install textract` |

---

## 6. Persisted State Files

### `blockchain.json`

**Purpose:** Persisted blockchain chain data (used by `blockchain.py`).

**Path:** `c:\Projects\certificateproject\blockchain.json`

**Structure:**
```json
{
  "chain": [
    {
      "index": 0,
      "timestamp": "2026-03-03T12:12:52.018845Z",
      "data": "Genesis Block",
      "previous_hash": "0",
      "hash": "799b01503060bf5014efd9195747ff556a4a7adf6ec5767dfb6f269f2059bc00"
    }
  ],
  "updated_at": "2026-03-03T12:29:47.276326Z"
}
```

**Created by:** `blockchain.py` `__init__()` → `_load_or_create()` → `save()`

### `blockchain.txt`

**Purpose:** Simple hash-based blockchain used by `app.py` routes.

**Path:** `c:\Projects\certificateproject\blockchain.txt`

**Format:** One SHA-256 hash per line.

**Created by:** `app.py` `add_certificate()` (appends hashes)

**Read by:** `app.py` `load_hashes()` (reads all lines)

### `issue_certificate.json`

**Purpose:** Legacy certificate storage from an earlier version.

**Path:** `c:\Projects\certificateproject\issue_certificate.json`

**Structure:**
```json
[
  {
    "index": 1,
    "timestamp": "2026-02-03T21:35:04.825519",
    "certificate_id": "Pyt2652022233437",
    "name": "Jayanth",
    "course": "Python Modules",
    "date": "10/18/2022",
    "hash": "1e9a0444c471fab8dbdb17dd82eb49a4195344c95bbf36e30823b97711264c21",
    "previous_hash": "0"
  }
]
```

**Used by:** `blockchain.py` `_load_legacy()` (auto-migrated to `blockchain.json`)

### `db.json`

**Purpose:** Legacy KV store used by `models/certificate_store.py`.

**Path:** `c:\Projects\certificateproject\db.json`

**Format:** JSON object mapping certificate IDs to hash values.

---

## 7. Runtime Directories

| Directory | Created By | Purpose | Created At |
|-----------|-----------|---------|-----------|
| `uploads/` | `app.py` line 29 | Uploaded certificate files | Startup |
| `uploads/certificates/` | `routes/upload.py` line 19 | Alternative upload directory | Request time |

---

## 8. Logging Configuration

### Standard Output

The primary application log (`app.py`) writes to stdout (console):

```python
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
```

### Werkzeug Log

Flask's development server uses its own logger (`werkzeug`) which logs HTTP requests to stdout.

### Log File

**File:** `extraction_system.log` (in project root)

**Content:** Flask/Werkzeug debug output captured from the console.

---

## 9. Startup Behavior Configuration

### Directory Creation

On startup, `app.py` creates the `uploads/` directory if it doesn't exist:
```python
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
```

### Blockchain Initialization

When `blockchain.py` is loaded:
1. Checks if `blockchain.json` exists
2. If yes: loads and validates the chain
3. If no: checks for legacy `issue_certificate.json` and migrates
4. If no legacy file: creates genesis block
5. If chain validation fails: attempts one-time reindex/relink/rehash

### Server Start

```python
if __name__ == "__main__":
    app.run(debug=True)
```

- Starts Flask development server
- `debug=True` enables auto-reload and debugger

---

## 10. Configuration Summary Table

| Aspect | Configuration Source | Value | Changeable Without Code Change |
|--------|-------------------|-------|-------------------------------|
| Upload directory | `app.py` constant | `"uploads"` | No |
| Blockchain file (app.py) | `app.py` constant | `"blockchain.txt"` | No |
| Blockchain file (blockchain.py) | `blockchain.py` constant | `"blockchain.json"` | No |
| Allowed extensions | `app.py` constant | `{"pdf", "png", "jpg", "jpeg", "doc", "docx"}` | No |
| Log level | `app.py` constant | `DEBUG` | No |
| Flask debug mode | `app.py` constant | `True` | No |
| Tesseract path | `ocr_utils.py` hardcoded | `C:\Program Files\Tesseract-OCR\tesseract.exe` | No |
| Poppler path | `app.py` hardcoded | `C:\poppler\Library\bin\poppler-25.12.0\Library\bin` | No |
| Extraction patterns | `config/extraction_patterns.py` | Various lists/dicts | **Yes** |
| Poppler path (refactored) | `models/ocr.py` env var | `POPPLER_PATH` | **Yes** (via environment variable) |

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview and technology stack |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [03_FILE_REFERENCE.md](03_FILE_REFERENCE.md) | Per-file reference |
| [07_DEPENDENCIES.md](07_DEPENDENCIES.md) | Dependency analysis |
| [08_DATA_STORAGE.md](08_DATA_STORAGE.md) | Storage mechanisms |