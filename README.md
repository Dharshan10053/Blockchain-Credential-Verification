# CertAuth: Immutable Certificate Verification Platform

CertAuth is an enterprise-grade, hybrid AI-powered certificate verification and credential management platform. It combines Google Gemini multimodal extraction, local OCR fallback, cryptographic blockchain ledger immutability, and dynamic PDF reporting into a unified, deployment-ready system.

## Problem Statement
In an era of rampant credential fraud, verifying the authenticity of digital certificates is typically a manual, slow, and error-prone process. Legacy systems struggle to parse differently formatted certificates, often losing critical data like long course titles or issuing authorities. Furthermore, traditional databases lack the immutability required to prove a credential hasn't been tampered with post-issuance.

## The Solution
CertAuth solves this by providing a unified pipeline:
1. **Intelligent Extraction**: Uses Gemini AI (with a robust local OCR fallback) to dynamically understand the layout of *any* certificate image, PDF, or DOCX, extracting the Candidate Name, Course Title, Issuing Authority, Date, and ID with extremely high accuracy.
2. **Immutability**: Cryptographically hashes the extracted payload and commits it to an append-only JSON blockchain ledger.
3. **Responsive Reporting**: Generates enterprise-grade, responsive PDF reports that elegantly handle exceptionally long titles without truncation.
4. **Instant Verification**: Generates QR codes that instantly route validators to a tamper-proof verification endpoint.

## Features & Capabilities
* **Hybrid Extraction Pipeline**: Primary Google Gemini Multimodal JSON extraction with graceful degradation to local EasyOCR/Tesseract.
* **Self-Healing Database**: Advanced `ON CONFLICT` payload repair logic ensures legacy records are automatically updated when re-verified.
* **Responsive PDF Reporting Engine**: Uses ReportLab to generate dynamic, premium PDF reports that perfectly map to the verified extraction payload without data clipping.
* **Tamper-Evident Ledger**: A local Blockchain implementation prevents malicious database alterations.
* **QR Validation**: Automatically issues verifiable QR codes for instant physical-to-digital bridging.
* **Defensive Fallback Normalization**: Centralized fallback resolvers ensure varying OCR synonym outputs (e.g., `course_name` vs `title`) uniformly map to the correct frontend and PDF fields.
* **Fake Detection Engine**: Intelligently identifies altered/tampered certificates by matching hashed payloads against the ledger.

## Technology Stack
* **Backend**: Flask (Python)
* **AI Extraction**: `google-generativeai` (Gemini 1.5 Flash / Flash Lite)
* **OCR Fallback**: `pytesseract`, `easyocr`, `pdf2image`, `opencv-python`
* **Database**: SQLite3 (`certificates.db`)
* **Ledger**: Python-based local Blockchain Hash Chain (`blockchain.json`)
* **Reporting**: `reportlab`
* **Frontend**: Vanilla HTML/CSS/JS (Enterprise Dark Theme, Glassmorphism UI)

## Installation Guide

### Prerequisites
- Python 3.10+
- Tesseract OCR (If using OCR fallback)
- Poppler (For PDF to Image conversion)

### Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/certauth.git
   cd certauth
   ```
2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Environment Variables:**
   Copy the example config and add your Gemini API Key.
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `GEMINI_API_KEY`.

### Running Locally
To run the server in development mode:
```bash
python app.py
```
The platform will be available at `http://127.0.0.1:5000`.

## Architecture & Workflows
See [Architecture Documentation](docs/architecture.md) for a deep dive into the hybrid extraction pipeline and the blockchain verification flow.

See [Deployment Documentation](docs/deployment.md) for production readiness guidelines.

## Screenshots
*(Add your screenshots to the `docs/screenshots/` folder)*
- Dashboard & Upload Flow
- Verification Success State
- Tamper-Evident Detection Alert
- Generated PDF Report

## Future Improvements
- Migration to PostgreSQL for high-concurrency production deployments.
- Transitioning the local JSON blockchain to a public smart-contract ledger (e.g., Ethereum/Polygon).
- Expanding the AI validation capabilities to automatically verify signatures against a known-issuer database.

## License
MIT License. See `LICENSE` for details.
