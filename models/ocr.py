"""
OCR and pattern-based extraction for certificate images/PDFs.

Uses config.extraction_patterns for all field detection so different
layouts and institutions are supported without hardcoding certificate text.
"""

import re
from typing import Tuple

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None  # type: ignore
    Image = None  # type: ignore

from config.extraction_patterns import (
    get_date_patterns,
    get_id_patterns,
    get_name_patterns,
    get_course_patterns,
)


def _normalize_text(text: str) -> Tuple[str, list, str]:
    """Normalize raw OCR text: collapse newlines, strip lines, return (text, lines, full_text)."""
    text = re.sub(r"\n+", "\n", text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    full_text = " ".join(lines)
    return text, lines, full_text


def _extract_by_regex(full_text: str, patterns: list, group: int = 1) -> str:
    """Try each regex; return first capture group or full match. Empty string = not found."""
    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            if match.groups():
                return (match.group(group) or "").strip()
            return (match.group(0) or "").strip()
    return ""


def _extract_date(lines: list, full_text: str) -> str:
    patterns = get_date_patterns()
    for pattern in patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return "Unknown"


def _extract_cert_id(lines: list, full_text: str) -> str:
    cfg = get_id_patterns()
    # Try regex first
    value = _extract_by_regex(full_text, cfg["regex"])
    if value:
        return value
    # Label-based: "ID: xyz" or "Certificate ID: xyz"
    for kw in cfg["label_keywords"]:
        pat = re.compile(re.escape(kw) + r"\s*[:\-]?\s*([A-Za-z0-9\-_]+)", re.IGNORECASE)
        match = pat.search(full_text)
        if match:
            return match.group(1).strip()
    return "Unknown"


def _extract_name(lines: list, full_text: str) -> str:
    cfg = get_name_patterns()
    lower_lines = [ln.lower() for ln in lines]

    # 1) Trigger phrase → next line
    for i, line in enumerate(lower_lines):
        if any(trigger in line for trigger in cfg["trigger_phrases"]):
            if any(skip in line for skip in cfg["trigger_skip_if_contains"]):
                continue
            if i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if candidate and len(candidate.split()) <= (cfg.get("fallback_max_words", 4)):
                    return candidate
                break

    # 2) Label on same line: "Name: John Doe"
    for i, line in enumerate(lines):
        low = line.lower()
        for kw in cfg["label_keywords"]:
            if kw in low:
                idx = low.find(kw)
                after = line[idx + len(kw) :].strip()
                if after and (not after.startswith(":") or len(after) > 1):
                    after = after.lstrip(":-").strip()
                if after and len(after.split()) <= (cfg.get("fallback_max_words", 4)):
                    return after
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
                break

    # 3) Fallback: short alpha-only line, not in exclude list, after min index
    min_idx = cfg.get("fallback_min_line_index", 2)
    exclude = set(cfg["fallback_exclude"])
    max_words = cfg.get("fallback_max_words", 4)
    for idx in range(min_idx, len(lines)):
        line = lines[idx]
        words = line.split()
        if 1 <= len(words) <= max_words:
            if not any(ex in line.lower() for ex in exclude):
                if all(w.isalpha() for w in words):
                    return line.strip()
    return "Unknown"


def _strip_invisible(s: str) -> str:
    """Remove control and other non-printable characters, then normalize whitespace."""
    s = "".join(c for c in s if c.isprintable() or c.isspace())
    return re.sub(r"\s+", " ", s).strip()


def _is_valid_course_line(candidate: str, cfg: dict) -> bool:
    """Return True if line is a valid course name candidate. All rules from config."""
    candidate = _strip_invisible(candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    if not candidate:
        return False

    max_words = cfg.get("max_words", 8)
    exclude_keywords = cfg.get("exclude_keywords", [])
    max_ratio = cfg.get("max_uppercase_ratio", 0.6)
    max_chars_period = cfg.get("max_chars_with_period", 40)
    max_commas = cfg.get("max_commas", 2)

    words = candidate.split()
    if len(words) > max_words:
        return False

    if candidate.isupper():
        return False
    letters = [c for c in candidate if c.isalpha()]
    if letters:
        upper_count = sum(1 for c in letters if c.isupper())
        if upper_count / len(letters) >= max_ratio:
            return False

    if len(candidate) > max_chars_period and candidate.rstrip().endswith("."):
        return False

    if candidate.count(",") > max_commas:
        return False

    candidate_lower = candidate.lower()
    for ex in exclude_keywords:
        if ex.lower() in candidate_lower:
            return False

    return True


def _extract_course(lines: list, full_text: str) -> str:
    cfg = get_course_patterns()
    max_words = cfg.get("max_words", 8)
    scan_forward = cfg.get("scan_forward_lines", 4)
    lower_lines = [ln.lower() for ln in lines]

    # 1) Trigger phrase → scan forward up to N lines for first valid course
    for i, line in enumerate(lower_lines):
        if any(trigger in line for trigger in cfg["trigger_phrases"]):
            if any(skip in line for skip in cfg["trigger_skip_if_contains"]):
                continue
            end = min(i + 1 + scan_forward, len(lines))
            for j in range(i + 1, end):
                candidate = lines[j]
                if _is_valid_course_line(candidate, cfg):
                    return _strip_invisible(candidate).strip()

    # 2) Label-based extraction
    for line in lines:
        low = line.lower()
        for kw in cfg["label_keywords"]:
            if kw in low:
                idx = low.find(kw)
                after = line[idx + len(kw) :].strip().lstrip(":-").strip()
                after = _strip_invisible(after)
                if after and len(after.split()) <= max_words and _is_valid_course_line(after, cfg):
                    return after
                break

    return "Unknown"


def extract_details(text: str) -> Tuple[str, str, str, str, str]:
    """
    Extract name, course, date, cert_id from OCR text using pattern config.
    Returns (name, course, date, cert_id, full_text).
    """
    _, lines, full_text = _normalize_text(text)
    name = "Unknown"
    course = "Unknown"
    date = "Unknown"
    cert_id = "Unknown"

    date = _extract_date(lines, full_text)
    if date == "":
        date = "Unknown"

    cert_id = _extract_cert_id(lines, full_text)
    name = _extract_name(lines, full_text)
    course = _extract_course(lines, full_text)

    return name, course, date, cert_id, full_text


def extract_text(file_path: str) -> str:
    """Extract text from image or PDF using Tesseract."""
    if pytesseract is None or Image is None:
        raise ImportError("pytesseract and Pillow are required for OCR")

    text = ""
    path_lower = file_path.lower()

    if path_lower.endswith(".pdf"):
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(file_path)
        except Exception:
            # Optional: poppler path on Windows
            import os
            poppler = os.environ.get("POPPLER_PATH")
            if poppler:
                from pdf2image import convert_from_path
                pages = convert_from_path(file_path, poppler_path=poppler)
            else:
                from pdf2image import convert_from_path
                pages = convert_from_path(file_path)
        for page in pages:
            text += pytesseract.image_to_string(page)
    else:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)

    return text
