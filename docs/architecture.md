# CertAuth System Architecture

The CertAuth system is designed as a secure, fault-tolerant pipeline.

## 1. Extraction Pipeline (Hybrid Mode)
When a user uploads a certificate (`.png`, `.jpg`, `.pdf`, `.docx`), the system routes it through `extractor_fixed.py`:
1. **Primary Layer (Gemini)**: The document is converted to Base64 and sent to the Gemini Multimodal API with a strict JSON-schema prompt. Gemini analyzes the layout, typography, and semantic context to extract `name`, `course`, `issuer`, `date`, and `certificate_id`.
2. **Fallback Layer (Local OCR)**: If Gemini is rate-limited or fails, the system gracefully degrades to `extractor.py`, utilizing `easyocr` or `pytesseract`. It applies regex patterns and layout heuristics (e.g., keyword scoring, positional weighting) to extract the same fields.

## 2. Normalization & Fallback Resolver
Extraction outputs vary. The AI might return `course_title` while OCR returns `course_name`. 
CertAuth utilizes a **Centralized Normalized Fallback Resolver**:
```python
course_title = result.get("course") or result.get("course_title") or result.get("course_name") or "Not Extracted"
```
This guarantees UI and PDF parity regardless of which extraction engine succeeded.

## 3. Blockchain Immutability
A cryptographic SHA-256 hash of the normalized payload is generated. 
1. **Insertion**: The payload is saved to the SQLite database.
2. **Ledger Commit**: The payload and hash are permanently appended to `blockchain.json`.
If a malicious actor alters the SQLite database, the system cross-references the hash against the blockchain ledger. A mismatch instantly triggers a "TAMPERED" alert, maintaining zero-trust credential integrity.

## 4. Self-Healing Database Layer
CertAuth utilizes an advanced `ON CONFLICT DO UPDATE SET` SQLite clause. If a legacy certificate (which previously failed to extract a long course title) is re-uploaded, the system extracts the full title and updates the existing database record, dynamically healing historical data loss.

## 5. Report Generation
The `report_generator.py` utilizes `reportlab` to construct dynamic PDF reports. It bypasses hardcoded slicing or truncations, utilizing native `Paragraph` elements to support exceptionally long course titles or issuer names, ensuring enterprise-grade responsive rendering.
