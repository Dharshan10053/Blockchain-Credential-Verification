"""
Intelligent certificate detail extractor.

Extracts:
  name, course, certificate_id, date, organization (issuer)

Issuer detection uses a multi-signal scoring system instead of naïve regex.
"""
from __future__ import annotations
import re
import difflib
import logging
from typing import Optional
from backend.utils.ai_extractor import ai_extract_details

logger = logging.getLogger(__name__)

# ── Known stop-words that should NOT be treated as names/issuers ─────────────
_STOP_WORDS = {
    "certificate", "certification", "this", "certifies", "that", "has",
    "successfully", "completed", "awarded", "presented", "hereby", "given",
    "with", "from", "and", "the", "for", "date", "issued", "authorized",
    "signature", "director", "president", "signed", "by", "on", "at",
    "congratulations", "course", "completion", "achievement",
}

# ── Issuer keyword signals ────────────────────────────────────────────────────
_ISSUER_KEYWORDS = [
    "university", "institute", "institution", "college", "school",
    "academy", "authority", "organization", "organisation", "council",
    "board", "foundation", "association", "corp", "corporation", "ltd",
    "inc", "pvt", "technologies", "tech", "solutions", "labs",
    "issued by", "certified by", "authorized by", "provided by",
    "offered by", "presented by", "a product of", "in association with",
]

# ── Date patterns ─────────────────────────────────────────────────────────────
_DATE_PATTERNS = [
    r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    r"\b(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\b",
    r"\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b",
    r"\b(\d{4})\b",  # last resort: year only
]

# ── Cert ID patterns ──────────────────────────────────────────────────────────
_CERT_ID_PATTERNS = [
    r"(?:certificate\s+(?:id|no|number|#)[:\s]+)([A-Z0-9\-]{4,30})",
    r"(?:cert(?:ification)?\s+(?:id|no|number)[:\s]+)([A-Z0-9\-]{4,30})",
    r"(?:serial\s+(?:no|number)[:\s]+)([A-Z0-9\-]{4,30})",
    r"(?:ID[:\s]+)([A-Z0-9\-]{4,30})",
    r"\b([A-Z]{2,6}[\-/]?\d{4,12})\b",
]

# ── Course / credential title patterns ───────────────────────────────────────
_COURSE_CONTEXT = [
    r"(?:course|program|training|workshop|seminar|subject|module)[:\s]+([^\n]{3,80})",
    r'(?:in|for|on|of)\s+["\']?([A-Z][^\n"\']{3,70})["\']?\s+(?:course|program|training|certification|workshop)',
    r'(?:completion\s+of|completing|completing\s+the)\s+["\']?([A-Z][^\n"\']{3,80})',
    r"(?:this\s+certifies?\s+(?:that\s+)?[^\n]{3,50}\s+(?:has\s+)?(?:completed?|finished?))\s+([^\n]{3,80})",
]


def extract_details(raw_text: str) -> dict:
    text = _normalise(raw_text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 🔹 Rule-based extraction
    result = {
        "name": _extract_name(text, lines),
        "course": _extract_course(text, lines),
        "certificate_id": _extract_cert_id(text),
        "date": _extract_date(text),
        "issuer": _extract_issuer(text, lines),
    }

    # 🔥 AI fallback if anything important missing
    if not result["name"] or not result["issuer"]:
        ai_result = ai_extract_details(text)

        if ai_result:
            result["name"] = result["name"] or ai_result.get("name", "")
            result["issuer"] = result["issuer"] or ai_result.get("issuer", "")
            result["course"] = result["course"] or ai_result.get("course", "")

    return result




# ── Normalisation ─────────────────────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Normalize text for better extraction."""
    text = text.replace("\r", "").replace("\x0c", "\n")
    # Collapse whitespace and preserve line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    # Remove noisy OCR characters while keeping basic punctuation
    text = re.sub(r'[^\w\s\.,\-/:]', '', text)
    return text.strip()


def _clean_line(line: str) -> str:
    """Trim and normalize a candidate line."""
    return re.sub(r'^[\W_]+|[\W_]+$', '', line).strip()


# ── Name extraction ───────────────────────────────────────────────────────────
def _is_valid_candidate_name(s: str) -> bool:
    words = s.split()

    if not 1 <= len(words) <= 3:
        return False

    if len(s) > 50:
        return False

    if not all(re.match(r'^[A-Za-z]+$', w) for w in words):
        return False

    lower_words = {w.lower() for w in words}

    if lower_words & _STOP_WORDS:
        return False

    if any(w.lower() in {
        "python", "module", "course", "training",
        "program", "certificate", "completion"
    } for w in words):
        return False

    return True
def _looks_like_name(s: str) -> bool:
    words = s.split()

    if not 1 <= len(words) <= 3:
        return False

    if len(s) > 50:
        return False

    # Allow only alphabets
    if not all(re.match(r'^[A-Za-z]+$', w) for w in words):
        return False

    lower_words = {w.lower() for w in words}

    # Reject stop words
    if lower_words & _STOP_WORDS:
        return False

    # Reject technical/course words
    if any(w.lower() in {
        "python", "module", "course", "training",
        "program", "certificate", "completion"
    } for w in words):
        return False

    return True

def _extract_name(text: str, lines: list[str]) -> str:
    n = len(lines)

    anchors = [
        "presented to",
        "awarded to",
        "certified to",
        "given to",
        "this certificate is presented to",
        "this is to certify that",
    ]

    # 🚀 STEP 1: STRICT anchor-based extraction (PRIMARY METHOD)
    for i, line in enumerate(lines):
        lower = line.lower()

        if any(anchor in lower for anchor in anchors):

            # Look next 1–3 lines (VERY IMPORTANT for real certificates)
            for j in range(1, 4):
                if i + j < n:
                    candidate = lines[i + j].strip()

                    # Accept even single word names (FIX)
                    if _is_valid_candidate_name(candidate):
                        return _clean_line(candidate)

    # 🚀 STEP 2: Strong fallback (rare case)
    candidates = []

    for i, line in enumerate(lines):
        if not _is_valid_candidate_name(line):
            continue

        lower = line.lower()
        pos = i / max(n, 1)
        score = 0

        # ✅ Middle is best
        if 0.2 < pos < 0.7:
            score += 3

        # ❌ Bottom = signature zone (CRITICAL FIX)
        if pos > 0.75:
            score -= 5

        # ❌ Strong penalty for roles
        if any(word in lower for word in [
            "founder", "ceo", "director", "president",
            "instructor", "trainer", "signature", "authorized"
        ]):
            score -= 6

        # ❌ Issuer-like
        if any(kw in lower for kw in _ISSUER_KEYWORDS):
            score -= 4

        # ✅ Short names preferred
        if 1 <= len(line.split()) <= 3:
            score += 1

        candidates.append((score, line))

    if candidates:
        candidates.sort(reverse=True)
        best_score, best = candidates[0]

        if best_score > 1:
            return _clean_line(best)

    return ""

def _name_score(line: str, pos: int, total: int, text_lower: str) -> float:
    """Score a line as a potential name."""
    score = 0.0
    lower_line = line.lower()

    # Context proximity
    context_keywords = ["awarded to", "presented to", "certified to", "given to", "this is to certify that"]
    for kw in context_keywords:
        idx = text_lower.find(kw)
        if idx != -1:
            line_start = text_lower.find(lower_line)
            if line_start != -1 and abs(line_start - idx) < 200:
                score += 3.0

    # Prefer title case names
    if line.istitle():
        score += 2.0
    elif line.isupper():
        score += 0.5

    # Position: names often appear near the keyword or middle section
    fraction = pos / max(total, 1)
    if 0.15 < fraction < 0.8:
        score += 0.5

    words = line.split()
    if len(words) == 2:
        score += 1.0
    elif len(words) == 3:
        score += 0.75

    if any(kw in lower_line for kw in _ISSUER_KEYWORDS):
        score -= 3.0
    if re.search(r"\b(course|training|program|certificate|completion|university|institute|authority|board|organization)\b", lower_line):
        score -= 3.0

    return score


# ── Course extraction ─────────────────────────────────────────────────────────

def _extract_course(text: str, lines: list[str]) -> str:
    for pattern in _COURSE_CONTEXT:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if 5 < len(candidate) < 100:
                return candidate

    # fallback scoring
    best = ""
    best_score = 0

    for i, line in enumerate(lines):
        lower = line.lower()

        if any(k in lower for k in ["course", "training", "program", "certification"]):
            score = 2

            if 0.3 < i / max(len(lines), 1) < 0.7:
                score += 1

            if len(line) < 100:
                score += 0.5

            if score > best_score:
                best_score = score
                best = line

    return best


def _course_score(line: str, pos: int, total: int, text: str) -> float:
    """Score a line as a potential course."""
    score = 0.0
    lower_line = line.lower()
    
    # Keywords: course, training, etc.
    course_keywords = ["course", "training", "program", "workshop", "certification", "completion", "subject", "module"]
    for kw in course_keywords:
        if kw in lower_line:
            score += 2.0
    
    # Position: prefer middle
    if 0.3 < pos / max(total, 1) < 0.7:
        score += 1.0
    
    # Capitalization: title case
    if line.istitle():
        score += 1.0
    
    # Length: reasonable
    if 5 < len(line) < 100:
        score += 0.5
    
    # Penalize if looks like name or issuer
    if _looks_like_name(line):
        score -= 3.0
    if any(kw in lower_line for kw in _ISSUER_KEYWORDS):
        score -= 2.0
    
    # Penalize dates or IDs
    if re.search(r'\d{4}', line) or re.match(r'^[A-Z0-9\-]+$', line):
        score -= 2.0
    
    return score


# ── Certificate ID ─────────────────────────────────────────────────────────────

def _extract_cert_id(text: str) -> str:
    for pat in _CERT_ID_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if re.match(r'[A-Z0-9\-]{4,}', candidate):  # Ensure alphanumeric
                return candidate
    return ""


# ── Date extraction ───────────────────────────────────────────────────────────

def _extract_date(text: str) -> str:
    for pat in _DATE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            # Validate format
            if re.match(r'\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}', candidate) or \
               re.match(r'\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}', candidate) or \
               re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', candidate, re.I) or \
               (len(candidate) == 4 and candidate.isdigit()):
                return candidate
    return ""


# ── Issuer / Organisation extraction (scoring) ────────────────────────────────

def _extract_issuer(text: str, lines: list[str]) -> str:
    if not lines:
        return ""

    n = len(lines)

    # 🔥 STEP 1: Try extracting from "by <org>"
    for line in lines[:8]:  # top lines
        match = re.search(r'by\s+([A-Za-z0-9 &]+)', line, re.I)
        if match:
            org = match.group(1).strip()
            if len(org) > 2:
                return org

    # 🔥 STEP 2: Try detecting brand-like top lines
    for i in range(min(6, n)):
        line = lines[i].strip()
        lower = line.lower()

        if any(x in lower for x in [
            "certificate", "completion", "presented", "awarded"
        ]):
            continue

        # likely org: short, contains caps, not name
        if (
            1 <= len(line.split()) <= 5 and
            any(c.isupper() for c in line) and
            not _is_valid_candidate_name(line)
        ):
            return line

    # 🔥 STEP 3: fallback scoring
    best = ""
    best_score = 0

    for i, line in enumerate(lines):
        lower = line.lower()
        pos = i / max(n, 1)
        score = 0

        # keywords
        if any(kw in lower for kw in _ISSUER_KEYWORDS):
            score += 3

        # top preference
        if pos < 0.3:
            score += 2

        # bottom penalty
        if pos > 0.75:
            score -= 3

        # reject roles
        if any(w in lower for w in [
            "founder", "ceo", "director", "president",
            "signature", "instructor"
        ]):
            score -= 5

        # reject names
        if _looks_like_name(line):
            score -= 3

        # length
        if 5 < len(line) < 80:
            score += 1

        if score > best_score:
            best_score = score
            best = line

    return best if best_score > 1 else ""
def _issuer_score(line: str, pos: int, total: int) -> float:
    score = 0.0
    lower = line.lower()

    # 1. Keyword presence
    for kw in _ISSUER_KEYWORDS:
        if kw in lower:
            score += 3.0

    # 2. Position weight — top 20% or bottom 20% of doc
    if pos / max(total, 1) <= 0.20:
        score += 1.5
    elif pos / max(total, 1) >= 0.80:
        score += 1.5

    # 3. Capitalisation ratio
    alpha_chars = [c for c in line if c.isalpha()]
    if alpha_chars:
        cap_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if cap_ratio > 0.5:
            score += 1.5
        elif line.istitle():
            score += 0.8

    # 4. Significant length (org names 8–60 chars)
    if 8 <= len(line) <= 60:
        score += 0.5

    # 5. Does NOT look like a person's name
    if _looks_like_name(line):
        score -= 2.0

    # 6. Does NOT look like a date / ID
    if re.match(r"^[\d\s\/\-\,]+$", line):
        score -= 3.0

    # 7. Penalise pure stopword lines
    words = set(line.lower().split())
    overlap = len(words & _STOP_WORDS) / max(len(words), 1)
    if overlap > 0.6:
        score -= 2.0

    return score


# ── Confidence score ──────────────────────────────────────────────────────────

def _compute_confidence(d: dict) -> float:
    provided = sum(1 for v in [
        d["name"],
        d["course"],
        d["certificate_id"],
        d["date"],
        d["issuer"]
    ] if v)

    base = (provided / 5) * 100
    return round(base, 1)
