# 12 — TODO ROADMAP

## Overview

This document provides a prioritized roadmap for the Certificate Authentication System. Items are organized by priority level and category. This roadmap is based on the current state of the project as documented in [11_CURRENT_STATUS.md](11_CURRENT_STATUS.md).

---

## Priority Levels

| Priority | Definition | Timeline |
|----------|-----------|----------|
| **Critical** | Blocks core functionality or security | Immediate (0-2 weeks) |
| **High** | Significant improvement or risk reduction | Short-term (2-6 weeks) |
| **Medium** | Important enhancement | Medium-term (2-3 months) |
| **Low** | Nice to have | Long-term (3-6 months) |
| **Future** | Enterprise or advanced feature | 6+ months |

---
## Architecture Status Update (2026-08-02)

### Decision
- ✅ `backend/` is approved as the future primary architecture.
- ✅ `app.py` remains the live application until migration is completed.
- ✅ Migration will be incremental to avoid regressions and preserve existing functionality.

### Key Findings
- Three generations of the application exist in the repository.
- `backend/` provides the most complete enterprise foundation.
- Duplicate implementations will be consolidated during migration.
- Gemini AI integration is deferred until after the backend migration.

## Critical Priority

### C1: Fix Template Rendering Bugs
**Issue:** `GET /issue` and `GET /verify` return `index.html` instead of `issue.html` and `verify.html`.
**Files:** `app.py` lines 839, 864
**Effort:** Minutes
**Impact:** Users can now access the issue and verify forms.

### C2: Add Error Message to Verify Validation Failure
**Issue:** `POST /verify` does not pass an error message to the template when file validation fails.
**Files:** `app.py` line 847
**Effort:** Minutes
**Impact:** Users see why verification failed.

### C3: Implement Authentication
**Issue:** No authentication — anyone can issue certificates.
**Files:** New files + `app.py`
**Effort:** Days
**Impact:** Basic access control. Issue endpoint requires authentication, verify endpoint is public.

### C4: Add CSRF Protection
**Issue:** Forms are vulnerable to cross-site request forgery.
**Files:** `app.py`, `templates/*.html`
**Effort:** Hours
**Impact:** Protection against CSRF attacks on form submissions.

### C5: Add Upload Size Limit
**Issue:** No `MAX_CONTENT_LENGTH` configured — unlimited uploads.
**Files:** `app.py`
**Effort:** Minutes
**Impact:** Prevents disk exhaustion DoS attacks.

### C6: Disable Debug Mode in Production
**Issue:** `app.run(debug=True)` exposes the Werkzeug debugger.
**Files:** `app.py` line 935
**Effort:** Minutes
**Impact:** Eliminates code execution risk from debugger.

### C7: Set Flask Secret Key
**Issue:** No `app.secret_key` configured.
**Files:** `app.py`
**Effort:** Minutes
**Impact:** Enables secure session management.

---

## High Priority

#### H1: Migrate to backend/ Architecture
**Status:** Approved

**Decision:** The `backend/` directory has been selected as the future primary architecture after a full repository audit.

**Migration Strategy:**
- Migrate incrementally.
- Preserve existing functionality.
- Maintain backward compatibility.
- Eliminate duplicate implementations only after successful migration.
- Keep `app.py` as the live compatibility layer until migration is complete.
**Impact:** Establishes a single enterprise architecture and removes long-term technical debt.

### H2: Consolidate Blockchain Implementations
**Issue:** Two blockchain implementations exist (`app.py` simple + `blockchain.py` full).
**Files:** `app.py`, `blockchain.py`
**Effort:** Days
**Impact:** Single, validated blockchain with block structure and chain integrity.
**Note:** This will be completed as part of the approved backend migration.

### H3: Consolidate Hashing Implementations
**Issue:** Two hashing implementations exist (`app.py` non-normalized + `utils/cert_hash.py` canonical).
**Files:** `app.py`, `utils/cert_hash.py`
**Effort:** Days
**Impact:** Canonical hashing ensures consistent hashes across OCR variations.
**Note:** This will use the canonical hashing implementation from `backend/`.

### H4: Add File Content Validation
**Issue:** Only file extension is validated, not content.
**Files:** `app.py` `allowed_file()`
**Effort:** Hours
**Impact:** Prevents upload of files with incorrect extensions.

### H5: Complete requirements.txt
**Issue:** 5 dependencies missing from `requirements.txt`.
**Files:** `requirements.txt`
**Effort:** Minutes
**Impact:** New developers can install all dependencies with one command.

### H6: Add API Key Authentication
**Issue:** API endpoints have no authentication.
**Files:** `app.py`
**Effort:** Days
**Impact:** API access requires valid API key.

### H7: Add Rate Limiting
**Issue:** API endpoints have no rate limiting.
**Files:** `app.py` (via Flask extension)
**Effort:** Hours
**Impact:** Prevents API abuse and DoS attacks.

### H8: Implement Audit Logging
**Issue:** No audit trail for certificate operations.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Tracks who issued which certificate and when.

### H9: Create Automated Test Suite
**Issue:** Only one manual test script exists.
**Files:** New `tests/` directory
**Effort:** Weeks
**Impact:** Ensures reliability and prevents regressions.

### H10: Configure CORS
**Issue:** No CORS configuration for API endpoints.
**Files:** `app.py` (via flask-cors)
**Effort:** Hours
**Impact:** Enables cross-origin API requests from web applications.

---

## Medium Priority

### M1: Integrate config/extraction_patterns.py
**Issue:** `app.py` has hardcoded patterns instead of using the configurable module.
**Files:** `app.py`, `config/extraction_patterns.py`
**Effort:** Days
**Impact:** Adding new certificate layouts becomes easier (just add patterns).

### M2: Add Hash Normalization to app.py
**Issue:** `app.py` hashes without normalization, causing verification failures on OCR variation.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Same certificate uploaded with different OCR output produces the same hash.

### M3: Display University and Year in Result Page
**Issue:** `result.html` does not display university or year fields.
**Files:** `app.py` lines 829-837, `templates/result.html`
**Effort:** Minutes
**Impact:** Complete certificate data is displayed.

### M4: Add File Cleanup Mechanism
**Issue:** Uploaded files accumulate indefinitely.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Prevents disk space exhaustion.

### M5: Use Environment Variables for Configuration
**Issue:** All paths and settings are hardcoded.
**Files:** `app.py`, `blockchain.py`
**Effort:** Hours
**Impact:** Portable configuration across environments.

### M6: Add Text Cleaning for Image OCR
**Issue:** `advanced_clean()` is only applied to PDF output, not image OCR.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Consistent text quality across all file types.

### M7: Add CI/CD Pipeline
**Issue:** No automated build, test, or deployment pipeline.
**Files:** New `.github/workflows/` or similar
**Effort:** Days
**Impact:** Automated testing and deployment.

### M8: Add Type Hints
**Issue:** `app.py` has no type hints.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Better IDE support, documentation, and error detection.

### M9: Add Upload File Size Validation
**Issue:** No file size check before processing.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Reject oversized files early, prevent memory issues.

### M10: Implement Structured Logging
**Issue:** Current logging is plain text, not structured.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Better log analysis and monitoring.

---

## Low Priority

### L1: Add Log Rotation
**Issue:** No log rotation configured.
**Files:** `app.py` or external config
**Effort:** Hours
**Impact:** Prevents log files from growing indefinitely.

### L2: Add PDF Page Count Validation
**Issue:** No limit on PDF page count for OCR processing.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Prevents processing of extremely long documents.

### L3: Add Image Dimension Validation
**Issue:** No limit on image dimensions for preprocessing.
**Files:** `app.py`
**Effort:** Hours
**Impact:** Prevents memory issues with extremely large images.

### L4: Add Cache for OCR Results
**Issue:** Every verification re-OCR's the certificate.
**Files:** `app.py` or new module
**Effort:** Days
**Impact:** Faster verification for previously processed certificates.

### L5: Add Progress Indicator for OCR
**Issue:** OCR can take several seconds with no user feedback.
**Files:** `templates/`, `static/js/`
**Effort:** Hours
**Impact:** Better user experience during processing.

### L6: Add File Type Detection by Magic Bytes
**Issue:** Only file extension is checked, not content.
**Files:** `app.py`
**Effort:** Hours
**Impact:** More accurate file type validation.

### L7: Pin Dependency Versions
**Issue:** requirements.txt uses minimum versions only.
**Files:** `requirements.txt`
**Effort:** Minutes
**Impact:** Reproducible builds.

### L8: Rename False Return Values
**Issue:** `verify_certificate()` returns "FAKE" instead of "NOT VERIFIED" or "INVALID".
**Files:** `app.py` line 802
**Effort:** Minutes
**Impact:** More professional terminology.

---

## Future Enhancements

### F1: Digital Signature Support
**Description:** Add cryptographic signing of certificates using public/private key pairs.
**Effort:** Weeks
**Impact:** Certificates can be cryptographically signed by the issuing authority.

### F2: QR Code Generation and Verification
**Description:** Generate QR codes containing certificate hashes for easy verification via mobile scanning.
**Effort:** Weeks
**Impact:** Mobile-friendly verification experience.

### F3: Certificate Revocation
**Description:** Allow administrators to revoke issued certificates.
**Effort:** Weeks
**Impact:** Full certificate lifecycle management.

### F4: Bulk Certificate Issuance
**Description:** Allow uploading a CSV/spreadsheet to issue multiple certificates at once.
**Effort:** Weeks
**Impact:** Efficient for large-scale issuance (e.g., university graduations).

### F5: Email Certificate Delivery
**Description:** Automatically email issued certificates to recipients.
**Effort:** Weeks
**Impact:** End-to-end certificate delivery workflow.

### F6: Admin Dashboard
**Description:** Dashboard with analytics, user management, and certificate statistics.
**Effort:** Months
**Impact:** Full administrative oversight.

### F7: Multi-Language OCR Support
**Description:** Support OCR for multiple languages (Tesseract language packs).
**Effort:** Days
**Impact:** International certificate support.

### F8: Blockchain Explorer
**Description:** Web interface to browse the blockchain and view certificate details.
**Effort:** Weeks
**Impact:** Transparency and audit capability.

### F9: IPFS/Decentralized Storage
**Description:** Store certificate images on IPFS for decentralized, permanent storage.
**Effort:** Months
**Impact:** Eliminates reliance on centralized file storage.

---

## Enterprise Features

### E1: Role-Based Access Control (RBAC)
**Description:** Admin, issuer, verifier, and viewer roles with granular permissions.
**Effort:** Months

### E2: LDAP/SSO Integration
**Description:** Enterprise authentication via LDAP, SAML, or OAuth.
**Effort:** Months

### E3: Database Migration
**Description:** Migrate from file-based storage to PostgreSQL/MySQL.
**Effort:** Months

### E4: Horizontal Scaling
**Description:** Support multiple application instances behind a load balancer.
**Effort:** Months

### E5: Audit Trail Database
**Description:** Immutable audit log for all certificate operations.
**Effort:** Weeks

### E6: Compliance Reporting
**Description:** Generate reports for audit compliance (SOC2, ISO 27001, etc.).
**Effort:** Months

### E7: Webhook Integrations
**Description:** Webhook notifications for certificate issuance and verification events.
**Effort:** Weeks

---

## Roadmap Timeline

```
Week 0-2 (Critical)
├── Fix template rendering bugs
├── Add error message to verify validation
├── Implement authentication
├── Add CSRF protection
├── Add upload size limit
├── Disable debug mode
└── Set Flask secret key

Week 2-6 (High Priority)
├── Integrate refactored modules
├── Consolidate blockchain implementations
├── Consolidate hashing implementations
├── Add file content validation
├── Complete requirements.txt
├── Add API authentication
├── Add rate limiting
├── Implement audit logging
├── Create automated test suite
└── Configure CORS

Month 2-3 (Medium Priority)
├── Integrate config/extraction_patterns.py
├── Add hash normalization
├── Display university and year in result
├── Add file cleanup mechanism
├── Use environment variables
├── Add text cleaning for image OCR
├── Add CI/CD pipeline
├── Add type hints
├── Add upload file size validation
└── Implement structured logging

Month 3-6 (Low Priority)
├── Add log rotation
├── Add PDF page count validation
├── Add image dimension validation
├── Add OCR result caching
├── Add progress indicator
├── Add magic byte detection
├── Pin dependency versions
└── Rename false return values

6+ Months (Future)
├── Digital signature support
├── QR code generation
├── Certificate revocation
├── Bulk issuance
├── Email delivery
├── Admin dashboard
├── Multi-language OCR
├── Blockchain explorer
└── IPFS storage
```

---

## Effort Estimation Summary

| Priority | Items | Estimated Effort |
|----------|-------|-----------------|
| Critical | 7 | ~1 week |
| High | 10 | ~4 weeks |
| Medium | 10 | ~4 weeks |
| Low | 8 | ~2 weeks |
| Future | 9 | ~3 months |
| Enterprise | 7 | ~6 months |

**Total estimated effort to production readiness:** ~3-4 months (excluding enterprise features)

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview and future vision |
| [11_CURRENT_STATUS.md](11_CURRENT_STATUS.md) | Current project status and known issues |
| [13_AI_GUIDELINES.md](13_AI_GUIDELINES.md) | Engineering rules for AI coding agents |