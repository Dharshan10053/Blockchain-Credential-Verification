"""
Pattern-based extraction config for certificate fields.

No certificate-specific text is hardcoded. Patterns use generic labels and
strategies so different institutions and layouts are supported by adding
or reordering patterns here.
"""

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Date: regex patterns (order matters; first match wins)
# ---------------------------------------------------------------------------

DATE_PATTERNS: List[str] = [
    r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b",
    r"\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b",
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*,?\s*\d{4}\b",
]


def get_date_patterns() -> List[str]:
    return list(DATE_PATTERNS)


# ---------------------------------------------------------------------------
# Certificate ID: regex patterns and label-based (e.g. "ID: xyz")
# ---------------------------------------------------------------------------

ID_REGEX_PATTERNS: List[str] = [
    r"(?:Id|ID|Certificate\s*ID)[:\s]+([A-Za-z0-9\-_]+)",
    r"(?:Cert\.?\s*#?|Ref\.?|Number)[:\s]*([A-Za-z0-9\-_]+)",
    r"\b([A-Z]{2,}[0-9]{4,}[A-Za-z0-9\-]*)\b",
    r"\b([A-Za-z]+\d{5,}[A-Za-z0-9\-]*)\b",
]

ID_LABEL_KEYWORDS: List[str] = [
    "id",
    "certificate id",
    "cert id",
    "ref",
    "reference",
    "number",
]


def get_id_patterns() -> Dict[str, Any]:
    return {
        "regex": list(ID_REGEX_PATTERNS),
        "label_keywords": list(ID_LABEL_KEYWORDS),
    }


# ---------------------------------------------------------------------------
# Name: context-based (trigger phrase → next line) and label-based
# ---------------------------------------------------------------------------

# Phrases that often appear on the line *before* the recipient name
NAME_TRIGGER_PHRASES: List[str] = [
    "presented to",
    "awarded to",
    "given to",
    "certified that",
    "recipient",
    "candidate",
    "awarded",
    "granted to",
    "this is to certify that",
    "is hereby awarded to",
]

# If the trigger line contains any of these, skip (e.g. "Certificate of Completion")
NAME_TRIGGER_SKIP_IF_CONTAINS: List[str] = [
    "certificate of completion",
    "certificate of participation",
    "certificate of achievement",
]

# Label-style: "Name: John Doe" or "Recipient: Jane"
NAME_LABEL_KEYWORDS: List[str] = [
    "name:",
    "recipient:",
    "candidate:",
    "awarded to:",
    "participant:",
]

# Fallback: exclude lines containing these when guessing a short name line
NAME_FALLBACK_EXCLUDE: List[str] = [
    "certificate",
    "completion",
    "course",
    "training",
    "founder",
    "director",
    "academy",
    "institute",
    "university",
    "college",
    "date",
    "id",
    "program",
    "verified",
    "issued",
]


def get_name_patterns() -> Dict[str, Any]:
    return {
        "trigger_phrases": list(NAME_TRIGGER_PHRASES),
        "trigger_skip_if_contains": list(NAME_TRIGGER_SKIP_IF_CONTAINS),
        "label_keywords": list(NAME_LABEL_KEYWORDS),
        "fallback_exclude": list(NAME_FALLBACK_EXCLUDE),
        "fallback_min_line_index": 2,
        "fallback_max_words": 4,
    }


# ---------------------------------------------------------------------------
# Course / program: trigger (e.g. "completed") → next line, or label
# ---------------------------------------------------------------------------

COURSE_TRIGGER_PHRASES: List[str] = [
    "completed",
    "completion of",
    "successfully completed",
    "for successfully completing",
    "has completed",
    "for completing",
    "for the course",
    "course entitled",
    "program:",
    "course:",
]

COURSE_TRIGGER_SKIP_IF_CONTAINS: List[str] = [
    "certificate of completion",
    "certificate of participation",
]

COURSE_LABEL_KEYWORDS: List[str] = [
    "course:",
    "program:",
    "training:",
    "module:",
    "subject:",
]

COURSE_MAX_WORDS = 8  # Avoid long sentences as course name

# When scanning forward after a trigger, skip lines containing these (e.g. titles/roles)
COURSE_EXCLUDE_KEYWORDS: List[str] = [
    "ceo",
    "founder",
    "certificate",
    "id",
    "date",
    "director",
    "signature",
]

COURSE_SCAN_FORWARD_LINES = 4  # Max lines to scan after trigger phrase

# Reject line if > this ratio of letters are uppercase (e.g. "MOSTLY CAPS")
COURSE_MAX_UPPERCASE_RATIO = 0.6

# Reject if line has more than 40 chars and ends with a period (sentence, not title)
COURSE_MAX_CHARS_WITH_PERIOD = 40

# Reject if line contains more than this many commas
COURSE_MAX_COMMAS = 2


def get_course_patterns() -> Dict[str, Any]:
    return {
        "trigger_phrases": list(COURSE_TRIGGER_PHRASES),
        "trigger_skip_if_contains": list(COURSE_TRIGGER_SKIP_IF_CONTAINS),
        "label_keywords": list(COURSE_LABEL_KEYWORDS),
        "max_words": COURSE_MAX_WORDS,
        "exclude_keywords": list(COURSE_EXCLUDE_KEYWORDS),
        "scan_forward_lines": COURSE_SCAN_FORWARD_LINES,
        "max_uppercase_ratio": COURSE_MAX_UPPERCASE_RATIO,
        "max_chars_with_period": COURSE_MAX_CHARS_WITH_PERIOD,
        "max_commas": COURSE_MAX_COMMAS,
    }
