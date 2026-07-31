# 13 — AI GUIDELINES

## Overview

This document provides engineering rules for future AI coding agents (Claude, GPT, Gemini, Cline, Copilot, Cursor, etc.) working on this project. Following these guidelines ensures consistency, preserves architecture, and maintains code quality.

---

## Core Principles

### P1: Read PROJECT_BRAIN Before Coding

**Rule:** Before making ANY changes to the codebase, read the relevant PROJECT_BRAIN documents first.

**Why:** The PROJECT_BRAIN contains the complete architectural context, design decisions, and current status of the project. Reading it prevents redundant work, breaking changes, and architectural violations.

**Checklist:**
- [ ] Read 00_PROJECT_OVERVIEW.md for project context
- [ ] Read 01_ARCHITECTURE.md for architectural understanding
- [ ] Read 03_FILE_REFERENCE.md for the files you're modifying
- [ ] Read 04_PIPELINES.md for execution flow
- [ ] Read 10_DESIGN_DECISIONS.md for rationale
- [ ] Read 11_CURRENT_STATUS.md for known issues
- [ ] Read 12_TODO_ROADMAP.md for prioritized tasks

### P2: Never Rewrite Working Functionality

**Rule:** Do not rewrite, refactor, or "improve" code that is working correctly. Only modify code to fix bugs, add features, or address technical debt.

**Why:** Unnecessary rewrites introduce risk, waste time, and may break working functionality.

**Exception:** If the code has security vulnerabilities, performance issues, or is blocking a feature, document the issue first and get approval before rewriting.

### P3: Preserve Architecture

**Rule:** Maintain the existing layered architecture. Do not introduce new architectural patterns without documenting the rationale.

**Why:** The project has a specific structure (Flask routes → OCR pipeline → extraction → hashing → blockchain). Changing this structure without understanding the full context can break the system.

### P4: Minimize Changes

**Rule:** Make the smallest possible change to accomplish the task. Each commit should be focused and minimal.

**Why:** Small changes are easier to review, test, and debug. They also reduce the risk of unintended side effects.

### P5: Keep Commits Focused

**Rule:** Each commit should address a single concern. Do not mix bug fixes, features, and refactoring in the same commit.

**Why:** Focused commits are easier to understand, revert, and cherry-pick.

### P6: Update Documentation After Changes

**Rule:** After making changes, update the relevant PROJECT_BRAIN documents. If the change affects architecture, update 01_ARCHITECTURE.md. If it adds a new file, update 02_DIRECTORY_STRUCTURE.md and 03_FILE_REFERENCE.md.

**Why:** The PROJECT_BRAIN is the source of truth. Outdated documentation is worse than no documentation.

---

## Coding Standards

### S1: Follow Existing Code Style

**Rule:** Match the existing code style in the file you're modifying. This includes:
- Indentation (4 spaces for Python)
- Naming conventions (snake_case for functions/variables, CamelCase for classes)
- String quotes (single quotes preferred in Python)
- Import ordering (stdlib first, then third-party, then local)

### S2: Add Type Hints

**Rule:** Add type hints to all new functions and modify existing ones when touched.

**Why:** Type hints improve IDE support, documentation, and error detection.

**Example:**
```python
def extract_name(lines: list[str], full_text: str) -> str:
    ...
```

### S3: Add Docstrings

**Rule:** Add docstrings to all new functions and classes. Use Google-style docstrings.

**Why:** Docstrings provide context and documentation for future developers.

**Example:**
```python
def extract_name(lines: list[str], full_text: str) -> str:
    """Extract recipient name from certificate text.
    
    Uses three strategies in order: label-based, trigger phrase, then fallback.
    
    Args:
        lines: List of text lines from OCR output
        full_text: Single-line merged text for cross-line matching
        
    Returns:
        Extracted name string, or "Not Provided" if not found
    """
```

### S4: Handle Errors Gracefully

**Rule:** Always handle errors with appropriate logging and fallback behavior. Use try/except blocks where operations can fail.

**Why:** The system is designed for graceful degradation. Errors should never crash the application.

### S5: Log Appropriately

**Rule:** Use the existing `logger` instance for all logging. Use appropriate levels:
- `DEBUG`: Detailed information for debugging
- `INFO`: Confirmation that things are working
- `WARNING`: Something unexpected happened but the system can continue
- `ERROR`: The system failed to perform a function

---

## Architecture Rules

### A1: Maintain the Monolithic-to-Modular Transition

**Rule:** The project is in transition from a monolithic `app.py` to a modular structure. When adding new functionality:
1. Add it to the appropriate refactored module (`routes/`, `models/`, `utils/`, `config/`)
2. If the module needs to be used by `app.py`, import it there
3. Do NOT duplicate functionality in both `app.py` and the refactored modules

### A2: Consolidate Blockchain Implementations

**Rule:** The `app.py` simple blockchain (`blockchain.txt`) should be replaced with the `blockchain.py` full implementation (`blockchain.json`). Do not create a third blockchain implementation.

**Migration path:**
1. Import `blockchain.py` in `app.py`
2. Replace `load_hashes()` + `add_certificate()` + `verify_certificate()` with `Blockchain` class methods
3. Migrate existing hashes from `blockchain.txt` to `blockchain.json`
4. Remove `blockchain.txt`-related code

### A3: Consolidate Hashing Implementations

**Rule:** The `app.py` simple hash function should be replaced with the `utils/cert_hash.py` canonical implementation.

**Migration path:**
1. Import `generate_cert_hash()` from `utils.cert_hash` in `app.py`
2. Replace `generate_hash()` with `generate_cert_hash()`
3. Update all callers to use the new function signature

### A4: Use Pattern-Based Extraction

**Rule:** New extraction patterns should be added to `config/extraction_patterns.py`, not hardcoded in `app.py`.

**Why:** The pattern-based approach allows supporting new certificate layouts without code changes.

### A5: Register Refactored Blueprints

**Rule:** When the refactored routes are ready, register them with the Flask app:
```python
from routes.upload import upload_bp
from routes.verify import verify_bp
app.register_blueprint(upload_bp)
app.register_blueprint(verify_bp)
```

---

## Security Rules

### SE1: Never Disable Security Checks

**Rule:** Do not remove or bypass security checks. If a check is too restrictive, fix it properly.

### SE2: Validate All Inputs

**Rule:** All user inputs must be validated:
- File extensions (already done)
- File content (MIME type, magic bytes)
- File size
- Upload size limits
- Form field values

### SE3: Use Environment Variables for Secrets

**Rule:** Never hardcode secrets, passwords, or API keys. Use environment variables with `os.environ.get()`.

### SE4: Add Authentication Before Authorization

**Rule:** Implement authentication first, then add role-based authorization. Do not add authorization without authentication.

### SE5: Sanitize All Output

**Rule:** All user-supplied data displayed in templates must be properly escaped. Jinja2 auto-escapes by default, but be careful when using `|safe` filter or rendering HTML directly.

---

## Testing Rules

### T1: Write Tests for New Features

**Rule:** All new features must have corresponding tests.

### T2: Use pytest

**Rule:** Use pytest as the testing framework. Add test files to a `tests/` directory.

### T3: Test Edge Cases

**Rule:** Test edge cases including:
- Empty files
- Corrupted files
- Very large files
- Files with no text
- Files with unusual layouts
- Missing fields

### T4: Maintain Test Coverage

**Rule:** Aim for at least 80% test coverage on the core OCR and extraction pipeline.

---

## Documentation Rules

### D1: Update PROJECT_BRAIN

**Rule:** After any significant change, update the relevant PROJECT_BRAIN documents:
- New files: Update 02_DIRECTORY_STRUCTURE.md and 03_FILE_REFERENCE.md
- New endpoints: Update 05_API_REFERENCE.md
- Architecture changes: Update 01_ARCHITECTURE.md and 10_DESIGN_DECISIONS.md
- New features: Update 00_PROJECT_OVERVIEW.md

### D2: Document Design Decisions

**Rule:** When making a significant design decision, document it in 10_DESIGN_DECISIONS.md with the appropriate category (Confirmed from code, Likely inference, or Unknown).

### D3: Keep README.md Updated

**Rule:** Update README.md with setup instructions, configuration changes, and new features.

---

## AI-Specific Guidelines

### AG1: Verify Before Assuming

**Rule:** Do not assume file contents, function behavior, or architecture. Use the PROJECT_BRAIN and source code to verify.

### AG2: Read Before Writing

**Rule:** Read the files you're modifying before making changes. Understand the existing code before adding to it.

### AG3: Explain Architectural Impact

**Rule:** When proposing changes, explain the architectural impact. How does this change affect the module relationships, data flow, or system architecture?

### AG4: Avoid Unnecessary Refactoring

**Rule:** Do not refactor code that is working correctly. Focus on the task at hand.

### AG5: Maintain Backward Compatibility

**Rule:** Changes should not break existing functionality. If a breaking change is necessary, document it clearly and provide migration instructions.

### AG6: Ask Before Making Breaking Changes

**Rule:** Before making changes that affect the API, data format, or architecture, ask for approval.

### AG7: One Task at a Time

**Rule:** Focus on one task at a time. Do not make unrelated changes while working on a task.

### AG8: Use the Task Progress System

**Rule:** Keep the task_progress checklist updated. This helps track progress and ensures nothing is missed.

---

## Quick Reference: Common Tasks

### Adding a New Certificate Layout
1. Add trigger phrases/labels to `config/extraction_patterns.py` (or `app.py`'s extraction functions)
2. Test with sample certificate
3. Update test_ocr.py if needed

### Adding a New OCR Engine
1. Add extraction function in `app.py` (following `_ocr_pdf()`, `_ocr_image_file()` pattern)
2. Add file extension to `ALLOWED_EXTENSIONS`
3. Add dispatch case in `perform_ocr()`
4. Update `requirements.txt`
5. Document in PROJECT_BRAIN

### Adding a New API Endpoint
1. Add route handler in `app.py` (or `routes/` blueprint)
2. Add validation
3. Add error handling
4. Document in 05_API_REFERENCE.md

### Adding Authentication
1. Install `flask_login`
2. Create user model (in `models/`)
3. Create login/logout routes
4. Add `@login_required` decorator to protected routes
5. Document in 09_SECURITY_REVIEW.md

---

## Related Documents

| Document | Description |
|----------|-------------|
| [00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md) | Project overview |
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | System architecture |
| [10_DESIGN_DECISIONS.md](10_DESIGN_DECISIONS.md) | Architectural decisions |
| [12_TODO_ROADMAP.md](12_TODO_ROADMAP.md) | Prioritized roadmap |