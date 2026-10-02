# Certificate Authentication System

Flask app that verifies certificate authenticity using a **blockchain-backed ledger**: issued certificates are hashed and stored in a persistent chain; verification checks the chain for a matching hash.

## Features

- **Persistent blockchain**: `blockchain.json` is the canonical certificate-membership ledger. On first use it imports `blockchain.txt` hashes once, backs up the existing JSON chain before migration, and leaves the text file read-only. SQLite stores certificate metadata and audit history, not certificate membership.
- **Pattern-based extraction**: Certificate fields (name, course, date, ID) are extracted from OCR text using configurable patterns—no hardcoded certificate wording.
- **Canonical hashing**: Certificate identity remains SHA-256 of `name|course|university|date|cert_id`; block-integrity hashes are separate.
- **Chain validation**: Block hashes and `previous_hash` links are validated on load.

## Setup

```bash
pip install -r requirements.txt
```

- **Tesseract** must be installed for OCR ([instructions](https://github.com/tesseract-ocr/tesseract)).
- **PDF support**: For PDF uploads, `pdf2image` and Poppler are required. On Windows, set `POPPLER_PATH` to your Poppler `bin` folder if needed.

## Run

```bash
python app.py
```

Then open the app (e.g. http://127.0.0.1:5000). Use **Verify Certificate** to check an image/PDF, or **Issue Certificate** to add one to the chain.

## Project structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for module roles and design choices.

## Possible extensions

- Digital signature support  
- QR code verification  
- Admin authentication  
- API endpoint for verification  

Cursor edit test completed.
