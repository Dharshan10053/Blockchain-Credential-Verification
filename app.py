from flask import Flask, render_template, request, jsonify
import os
import hashlib
import logging
import re
import secrets
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import fitz  # PyMuPDF
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
# Load environment variables from a local .env file (see .env.example).
# Safe to call even if no .env file exists.
load_dotenv()
# ----------------------------------
# ENVIRONMENT / RUNTIME MODE
# ----------------------------------
# FLASK_ENV controls debug mode and log verbosity. Defaults to "production"
# (safe-by-default) so debug mode is never accidentally enabled on a real
# deployment. Set FLASK_ENV=development locally to get the debugger + reloader.
FLASK_ENV = os.environ.get("FLASK_ENV", "production").lower()
IS_DEVELOPMENT = FLASK_ENV == "development"
# ----------------------------------
# LOGGING
# ----------------------------------
logging.basicConfig(
    level=logging.DEBUG if IS_DEVELOPMENT else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)
# ----------------------------------
# SECRET KEY / SESSION CONFIG
# ----------------------------------
# Required for signed sessions and CSRF protection. Reads from the SECRET_KEY
# env var in production. Falls back to an ephemeral per-process random key so
# local/dev runs still work without a .env file -- sessions just won't
# survive a restart in that case, which is fine for development.
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    if not IS_DEVELOPMENT:
        # Fail safely at startup rather than silently running production
        # with an ephemeral key: an ephemeral key invalidates all sessions
        # and CSRF tokens on every restart/worker respawn and offers no
        # durable secret to protect them in the meantime.
        raise RuntimeError(
            "SECRET_KEY is not set. Refusing to start in production "
            "(FLASK_ENV=production) without a persistent SECRET_KEY. Set "
            "SECRET_KEY in the environment (see .env.example), or set "
            "FLASK_ENV=development for local runs."
        )
    _secret_key = secrets.token_hex(32)
app.secret_key = _secret_key
# ----------------------------------
# ADMIN AUTHENTICATION (Authentication Foundation Layer)
# ----------------------------------
# Certificate issuance is a privileged action; verification stays public.
# A single shared admin key is used, accepted via the `X-Admin-Key` header
# (API clients) or the `admin_key` form field (web UI). Query-string keys are
# never accepted: they leak into server access logs and browser history.
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    logger.warning(
        "ADMIN_API_KEY is not set. Certificate issuance is disabled until "
        "an admin key is configured -- set ADMIN_API_KEY in the environment "
        "(see .env.example). Verification remains public and unaffected."
    )
def _admin_key_from_request():
    """Extract the caller-supplied admin key from header or form field."""
    return request.headers.get("X-Admin-Key") or request.form.get("admin_key")
def _is_valid_admin_key(candidate) -> bool:
    """Constant-time comparison against the configured admin key.
    Returns False (never raises) if no key is configured or none was
    supplied, so issuance fails safely closed rather than open.
    """
    if not ADMIN_API_KEY or not candidate:
        return False
    return secrets.compare_digest(candidate, ADMIN_API_KEY)
def _admin_key_error_message() -> str:
    if not ADMIN_API_KEY:
        return "Certificate issuance is disabled: no admin key is configured on the server."
    return "A valid admin key is required to issue certificates."
# ----------------------------------
# UPLOAD LIMITS
# ----------------------------------
UPLOAD_FOLDER = "uploads"
BLOCKCHAIN_FILE = "blockchain.txt"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
# Reject request bodies over 16 MB before they ever hit disk (DoS mitigation).
# Certificates are small documents/images; 16 MB is generous headroom.
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
# ----------------------------------
# CSRF PROTECTION
# ----------------------------------
# Protects the /issue and /verify HTML forms against cross-site request
# forgery. JSON API endpoints (/api/issue, /api/verify) are exempted below
# since they are not browser-form based and CSRF tokens don't apply to them.
csrf = CSRFProtect(app)
# ----------------------------------
# RATE LIMITING
# ----------------------------------
# In-memory limiter -- adequate for a single-process deployment. If this app
# is ever run with multiple workers/instances, swap storage_uri for a shared
# backend (e.g. Redis) so limits are enforced globally, not per-process.
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
# ----------------------------------
# FILE VALIDATION
# ----------------------------------
def allowed_file(filename: str) -> bool:
    if not filename:
        return False
    filename = filename.strip()
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS
def _save_uploaded_file(file) -> str:
    """Sanitize the filename with secure_filename(), then make it unique
    with a random token so concurrent/repeat uploads never overwrite an
    existing file on disk. Saves the file and returns the saved filepath.
    """
    base_name = secure_filename(file.filename)
    stem, dot, ext = base_name.rpartition(".")
    unique_token = secrets.token_hex(8)
    if dot:
        filename = f"{stem}_{unique_token}.{ext}"
    else:
        filename = f"{base_name}_{unique_token}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filepath
# ----------------------------------
# IMAGE PREPROCESSING
# ----------------------------------
def _deskew(gray: np.ndarray) -> np.ndarray:
    """Correct skew angle using minAreaRect on dark pixel coordinates."""
    try:
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 50:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5:
            return gray
        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w // 2, h // 2), -angle, 1.0)
        return cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception as e:
        logger.debug("Deskew failed: %s", e)
        return gray
def _preprocess_for_ocr(img_cv: np.ndarray) -> np.ndarray:
    """
    Full preprocessing pipeline for best OCR accuracy:
      1. Upscale if image is small (improves Tesseract character recognition)
      2. Convert to grayscale
      3. Gaussian blur  (smooth noise before thresholding)
      4. Denoise with Non-Local Means
      5. Deskew (rotation correction)
      6. Otsu binarization
    """
    # 1. Upscale small images
    h, w = img_cv.shape[:2]
    if max(h, w) < 1500:
        scale = 2.0
        img_cv = cv2.resize(
            img_cv, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )
    # 2. Grayscale
    gray = (
        cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        if len(img_cv.shape) == 3
        else img_cv.copy()
    )
    # 3. Gaussian blur — reduces high-frequency noise before binarization
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # 4. Denoise with Non-Local Means for residual noise
    gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)
    # 5. Deskew
    gray = _deskew(gray)
    # 6. Otsu binarization
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary
def _ocr_image_cv(img_cv: np.ndarray) -> str:
    """
    Run Tesseract with multiple PSM configs on a preprocessed OpenCV image.
    Returns whichever result has the most content.
    """
    processed = _preprocess_for_ocr(img_cv)
    configs = [
        "--oem 3 --psm 6",  # Assume uniform block of text
        "--oem 3 --psm 4",  # Single column of text
        "--oem 3 --psm 3",  # Fully automatic page segmentation
    ]
    best = ""
    for cfg in configs:
        try:
            result = pytesseract.image_to_string(processed, config=cfg)
            if len(result.strip()) > len(best.strip()):
                best = result
        except Exception as e:
            logger.debug("Tesseract config %s failed: %s", cfg, e)
    return best
def _ocr_image_with_layout(img_cv: np.ndarray) -> dict:
    """
    OCR with layout information using pytesseract.image_to_data().
    Returns structured OCR blocks with coordinates.
    """
    processed = _preprocess_for_ocr(img_cv)
    data = pytesseract.image_to_data(
        processed,
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT
    )
    blocks = []
    n = len(data["text"])
    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue
        blocks.append({
            "text": text,
            "x": data["left"][i],
            "y": data["top"][i],
            "w": data["width"][i],
            "h": data["height"][i],
            "conf": int(data["conf"][i])
        })
    return blocks
def _detect_name_from_layout(blocks: list) -> str:
    """
    Detect certificate name using OCR layout coordinates.
    Finds largest centered text block (typical certificate layout).
    """
    candidates = []
    for b in blocks:
        text = b["text"].strip()
        if len(text.split()) < 2 or len(text.split()) > 4:
            continue
        if not re.match(r"^[A-Za-z\s]+$", text):
            continue
        score = 0
        # larger text usually indicates name
        score += b["h"]
        # good OCR confidence
        score += b["conf"] / 10
        candidates.append((text, score))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]
# ----------------------------------
# OCR FUNCTIONS
# ----------------------------------
def _ocr_image_file(file_path: str) -> str:
    """OCR for JPG/PNG/JPEG with full preprocessing pipeline."""
    img = cv2.imread(file_path)
    if img is None:
        logger.warning("Could not read image: %s", file_path)
        return ""
    text = _ocr_image_cv(img)
    logger.debug("Image OCR: %d chars extracted", len(text))
    return text
def _text_from_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        return ""
    try:
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text and p.text.strip())
    except Exception as e:
        logger.warning("DOCX extraction failed: %s", e)
        return ""
def _text_from_doc(file_path: str) -> str:
    """Best-effort extraction for legacy .doc files via textract."""
    try:
        import textract  # type: ignore
        raw = textract.process(file_path)
        return raw.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning("DOC extraction failed: %s", e)
        return ""
def _ocr_pdf(file_path: str) -> str:
    """
    High-accuracy PDF text extraction pipeline.
    Step 1: Digital text extraction with PyMuPDF.
    Step 2: High-DPI OCR fallback with OpenCV preprocessing and multi-PSM Tesseract.
    Step 3: Advanced text cleaning and structured formatting.
    """
    import fitz
    import cv2
    import numpy as np
    import re
    import pytesseract
    from pdf2image import convert_from_path
    poppler_path = r"C:\poppler\Library\bin\poppler-25.12.0\Library\bin"
    def advanced_clean(text: str) -> str:
        if not text:
            return ""
        # 1. Remove non-printable/garbage characters (keep ASCII + newlines)
        text = re.sub(r"[^\x20-\x7E\n]", "", text)
        
        # 2. Remove isolated symbols like >, &, %, |, \, /, _, ~, - when they appear alone
        # These are often OCR artifacts in bad scans
        text = re.sub(r"(?<!\S)[>&%|\\/_~-](?=\s|$)", "", text)
        
        # 3. Collapse multiple spaces into one
        text = re.sub(r"[ \t]+", " ", text)
        
        # 4. Normalize newlines: Remove empty lines, then join lines that look like broken sentences
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        cleaned_lines = []
        for i, line in enumerate(lines):
            # Remove artifacts like "Page 1", "Page 1 of 2"
            if re.search(r"(?i)^Page\s+\d+(\s+of\s+\d+)?$", line):
                continue
            cleaned_lines.append(line)
            
        # Join lines but keep distinct certificate fields separate
        # (We join lines that don't end in punctuation if the next line starts with lowercase, 
        # but for certificates, usually keeping them separate is better for label extraction)
        return "\n".join(cleaned_lines).strip()
    # --- STEP 1: Digital Text Extraction (PyMuPDF) ---
    digital_text_parts = []
    try:
        doc = fitz.open(file_path)
        for page in doc:
            # Extract blocks to maintain layout integrity
            blocks = page.get_text("blocks")
            # Sort blocks by vertical (y) then horizontal (x) position
            blocks.sort(key=lambda b: (b[1], b[0]))
            
            for b in blocks:
                block_text = b[4].strip()
                if block_text:
                    digital_text_parts.append(block_text)
        doc.close()
    except Exception as e:
        logger.warning(f"Digital extraction failed: {e}")
    combined_digital = "\n".join(digital_text_parts)
    cleaned_digital = advanced_clean(combined_digital)
    # If we have significant digital text, return it immediately
    if len(cleaned_digital) > 200:
        logger.info(f"Digital extraction successful ({len(cleaned_digital)} chars)")
        return cleaned_digital
    # --- STEP 2: High Quality OCR Fallback ---
    logger.info("Insufficient digital text. Starting high-quality OCR fallback.")
    ocr_results = []
    try:
        # Use high DPI (450) for maximum character clarity
        pages = convert_from_path(file_path, dpi=450, poppler_path=poppler_path)
        
        for i, page_img in enumerate(pages):
            # Convert PIL image to OpenCV format
            cv_img = cv2.cvtColor(np.array(page_img), cv2.COLOR_RGB2BGR)
            
            # Use existing project preprocessing (Grayscale, Denoise, Deskew, Otsu)
            # This is Step 2's preprocessing requirement
            processed = _preprocess_for_ocr(cv_img)
            
            # Run multiple PSM modes to find the best layout recognition
            # psm 3: Auto page segmentation
            # psm 4: Single column of text
            # psm 6: Single uniform block of text
            psm_modes = ["3", "4", "6"]
            best_text = ""
            max_score = -1
            
            for mode in psm_modes:
                config = f"--oem 3 --psm {mode}"
                try:
                    raw_ocr = pytesseract.image_to_string(processed, config=config)
                    # Score based on meaningful words (2+ alphabetic characters)
                    words = re.findall(r'[a-zA-Z]{2,}', raw_ocr)
                    score = len(words)
                    
                    if score > max_score:
                        max_score = score
                        best_text = raw_ocr
                except Exception as e:
                    logger.debug(f"PSM {mode} failed: {e}")
            
            if best_text:
                ocr_results.append(best_text)
            
            logger.debug(f"OCR Page {i+1} processed (Best PSM score: {max_score})")
    except Exception as e:
        logger.error(f"OCR Fallback failed: {e}")
        return cleaned_digital # Return whatever we got from Step 1
    # --- STEP 3: Final Cleaning ---
    final_text = "\n\n".join(ocr_results)
    cleaned_ocr = advanced_clean(final_text)
    
    if not cleaned_ocr.strip():
        logger.warning("No text could be extracted from PDF via OCR.")
        return cleaned_digital
    return cleaned_ocr
def perform_ocr(filepath: str) -> str:
    """Route to the appropriate extractor based on file extension."""
    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    try:
        if ext == "pdf":
            text = _ocr_pdf(filepath)
        elif ext in {"png", "jpg", "jpeg"}:
            text = _ocr_image_file(filepath)
        elif ext == "docx":
            text = _text_from_docx(filepath)
        elif ext == "doc":
            text = _text_from_doc(filepath)
        else:
            text = ""
        logger.info(
            "\n%s\nOCR RAW TEXT (%d chars):\n%s\n%s",
            "=" * 60, len(text), text[:2000], "=" * 60,
        )
        return text or ""
    except Exception as e:
        logger.error("OCR Error: %s", e)
        return ""
# ----------------------------------
# FIELD EXTRACTION HELPERS
# ----------------------------------
NOT_PROVIDED = "Not Provided"
def _clean(s: str) -> str:
    """Collapse whitespace and strip punctuation borders."""
    return re.sub(r"\s+", " ", (s or "").strip()).strip(" .,:;-")
def _valid(value: str) -> str:
    """
    Return the value if it looks meaningful, otherwise NOT_PROVIDED.
    Rejects: empty strings, single characters, whitespace-only.
    """
    v = (value or "").strip()
    if not v or len(v) <= 1:
        return NOT_PROVIDED
    return v
def _label_extract(lines: list, full_text: str, labels: list, max_words: int = 10) -> str:
    """
    Search for 'Label: value' patterns across lines and full_text.
    Returns the first matching value, or empty string if none found.
    """
    for line in lines:
        for lbl in labels:
            pat = re.compile(re.escape(lbl) + r"\s*[:\-]?\s*(.+)", re.IGNORECASE)
            m = pat.search(line)
            if m:
                val = _clean(m.group(1))
                if val and len(val.split()) <= max_words:
                    return val
    # Also scan single-line merged full_text (catches cross-newline labels)
    for lbl in labels:
        pat = re.compile(re.escape(lbl) + r"\s*[:\-]\s*([^\n]{2,80})", re.IGNORECASE)
        m = pat.search(full_text)
        if m:
            val = _clean(m.group(1))
            if val and len(val.split()) <= max_words:
                return val
    return ""
# ----------------------------------
# FIELD EXTRACTORS
# ----------------------------------
def _extract_name(lines: list, full_text: str) -> str:
    # 1) Label-based: "Name: ...", "Student Name: ...", etc.
    label_result = _valid(_label_extract(
        lines, full_text,
        [
            "student name", "recipient name", "awarded to", "presented to",
            "participant name", "candidate name", "name",
        ],
        max_words=6,
    ))
    if label_result != NOT_PROVIDED:
        return label_result
    # 2) Trigger phrase → same line or next line
    triggers = [
        "this is to certify that",
        "certify that",
        "awarded to",
        "presented to",
        "this certifies that",
        "hereby awarded to",
        "is presented to",
    ]
    skip_if = ["certificate of", "completion", "participation", "achievement"]
    for i, line in enumerate(lines):
        low = line.lower()
        if any(sk in low for sk in skip_if):
            continue
        for trig in triggers:
            if trig in low:
                # Same-line value after the trigger
                after = _clean(line[low.find(trig) + len(trig):])
                after = re.sub(r"^(to\s+)?", "", after, flags=re.IGNORECASE).strip()
                after = re.split(r"\b(for|has|on|in|of)\b", after, maxsplit=1,
                                 flags=re.IGNORECASE)[0]
                after = _clean(after)
                if after and 1 <= len(after.split()) <= 6:
                    return _valid(after)
                # Next-line fallback
                if i + 1 < len(lines):
                    cand = _clean(lines[i + 1])
                    words = cand.split()
                    if (
                        1 <= len(words) <= 6
                        and re.search(r"[A-Za-z]", cand)
                        and all(re.match(r"[A-Za-z'\-\.]+$", w) for w in words)
                    ):
                        return _valid(cand)
                break
    # 3) Fallback: short, capitalized, all-alpha line unlikely to be a label
    exclude = {
        "certificate", "completion", "course", "training", "university",
        "institute", "college", "program", "verified", "issued", "date",
        "director", "founder", "signature", "blockchain",
    }
    for idx in range(2, len(lines)):
        line = lines[idx]
        words = line.split()
        if 1 <= len(words) <= 4:
            if not any(ex in line.lower() for ex in exclude):
                if all(re.match(r"[A-Za-z'\-\.]+$", w) for w in words):
                    if any(w[0].isupper() for w in words):
                        return _valid(line)
    return NOT_PROVIDED
def _extract_course(lines: list, full_text: str) -> str:
    # 0) Certificate title immediately before "Certificate of Completion"
    for i, line in enumerate(lines):
        if "certificate of completion" in line.lower():
            candidates = []

            for j in range(max(0, i - 3), i):
                cand = _clean(lines[j])
                low = cand.lower()

                if not cand:
                    continue

                if any(x in low for x in [
                    "certificate", "completion", "participant",
                    "presented to", "awarded to"
                ]):
                    continue

                words = cand.split()
                if 1 <= len(words) <= 10:
                    candidates.append(cand)

            if candidates:
                title = " ".join(candidates[-2:])

                if len(title.split()) <= 12:
                    return _valid(title)

                return _valid(candidates[-1])

    # 1) Label-based
    label_result = _valid(_label_extract(
        lines, full_text,
        [
            "course name", "course", "program", "programme",
            "training", "module", "subject", "field of study", "degree",
        ],
        max_words=10,
    ))
    if label_result != NOT_PROVIDED:
        return label_result
    # 2) Explicit degree patterns
    degree_pats = [
        r"\bBachelor\s+of\s+[A-Za-z&\.\s]{2,60}",
        r"\bMaster\s+of\s+[A-Za-z&\.\s]{2,60}",
        r"\bDoctor\s+of\s+[A-Za-z&\.\s]{2,60}",
        r"\bB\.?\s?Tech\b[A-Za-z\s\(\)]*",
        r"\bM\.?\s?Tech\b[A-Za-z\s\(\)]*",
        r"\bB\.?\s?Sc\b[A-Za-z\s\(\)]*",
        r"\bM\.?\s?Sc\b[A-Za-z\s\(\)]*",
        r"\bB\.?\s?E\b[A-Za-z\s\(\)]*",
        r"\bDiploma\s+in\s+[A-Za-z&\.\s]{2,60}",
        r"\bCertificate\s+in\s+[A-Za-z&\.\s]{2,60}",
    ]
    for line in lines:
        for pat in degree_pats:
            m = re.search(pat, line, flags=re.IGNORECASE)
            if m:
                val = _valid(_clean(m.group(0)))
                if val != NOT_PROVIDED and len(val.split()) <= 10:
                    return val
    # 3) Trigger phrase → scan forward for a valid course line
    triggers = [
        "completed", "completion of", "successfully completed",
        "for completing", "course entitled", "for the course",
        "has completed", "for successfully completing",
    ]
    skip_if = ["certificate of completion", "certificate of participation"]
    course_exclude = {"ceo", "founder", "certificate", "id", "date", "director", "signature"}
    for i, line in enumerate(lines):
        low = line.lower()
        if any(sk in low for sk in skip_if):
            continue
        if any(trig in low for trig in triggers):
            for j in range(i + 1, min(i + 5, len(lines))):
                cand = _clean(lines[j])
                words = cand.split()
                if 1 <= len(words) <= 10 and not any(ex in cand.lower() for ex in course_exclude):
                    return _valid(cand)
    return NOT_PROVIDED
def _extract_date(full_text: str) -> str:
    # 1) Label-based date extraction
    date_labels = [
        "date of issue", "issue date", "date of award", "awarded on",
        "issued on", "date of completion", "completion date",
    ]

    for lbl in date_labels:
        pat = re.compile(
            re.escape(lbl) + r"\s*[:\-]?\s*([^\n]{4,40})",
            re.IGNORECASE,
        )
        m = pat.search(full_text)

        if m:
            candidate = _clean(m.group(1))

            if re.search(r"\d{1,4}", candidate):
                return _valid(candidate[:40])

    # 2) Common date formats
    date_patterns = [
        # July 30th, 2024 / March 4, 2026
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",

        # 4th March 2026 / 4 March 2026
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s*,?\s*\d{4}\b",

        # 04/03/2026 or 2026-03-04
        r"\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b",
        r"\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b",
    ]

    for pat in date_patterns:
        m = re.search(pat, full_text, flags=re.IGNORECASE)

        if m:
            return _valid(_clean(m.group(0)))

    return NOT_PROVIDED

def _extract_cert_id(full_text: str) -> str:
    # 1) Label-based
    id_labels = [
        "certificate no", "certificate number", "certificate id",
        "cert no", "cert id", "cert. no", "registration no",
        "registration number", "ref no", "reference no",
        "id no", "serial no", "enrollment no",
        "enrolment verification code",
        "enrollment verification code",
        "user verification code",
        "verification code",
    ]
    for lbl in id_labels:
        pat = re.compile(
            re.escape(lbl) + r"\s*[:\-\.]?\s*([A-Za-z0-9\-_\/\.]+)",
            re.IGNORECASE,
        )
        m = pat.search(full_text)
        if m:
            val = _valid(_clean(m.group(1)))
            if val != NOT_PROVIDED and len(val) >= 3:
                return val
    # 2) Structural ID patterns (standalone alphanumeric codes)
    id_patterns = [
        r"\b([A-Z]{2,6}[\-\/]?\d{4}[\-\/][A-Za-z0-9\-]{3,})\b",
        r"\b(CERT[\-\.][A-Za-z0-9\-\.]{4,20})\b",
        r"\b([A-Z]{2,6}\d{5,12})\b",
        r"\b([A-Za-z]{2,4}[\-]?\d{6,})\b",
    ]
    for pat in id_patterns:
        m = re.search(pat, full_text)
        if m:
            return _valid(m.group(1))
    # 3) Extract ID from verification URL (VERY COMMON IN CERTIFICATES)
    url_patterns = [
        r"verify\/([A-Za-z0-9]+)",
        r"certificate\/([A-Za-z0-9]+)",
        r"id=([A-Za-z0-9]+)",
        r"cert\/([A-Za-z0-9]+)"
    ]
    for pat in url_patterns:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            val = _valid(_clean(m.group(1)))
            if val != NOT_PROVIDED:
                return val
    return NOT_PROVIDED
def _extract_university(lines: list) -> str:
    """
    Extract issuing organization (university/company).
    Works for universities, institutes, academies, and companies.
    """
    uni_keywords = (
        "university", "institute", "college", "academy",
        "school of", "department of", "faculty of"
    )
    org_keywords = (
        "devtown", "coursera", "udemy", "aws", "google",
        "microsoft", "ibm", "oracle", "meta", "edx", "forage"
    )
    candidates = []
    for line in lines:
        clean = _clean(line)
        lower = clean.lower()
        # Skip short lines
        if len(clean.split()) < 1:
            continue
        score = 0
        # University keyword match
        if any(k in lower for k in uni_keywords):
            score += 5
        # Organization keyword match
        if any(k in lower for k in org_keywords):
            score += 6
        # Good length for institution name
        if 2 <= len(clean.split()) <= 8:
            score += 2
        # Avoid student name detection
        if re.fullmatch(r"[A-Z\s]+", clean):
            score -= 2
        if score > 0:
            candidates.append((clean, score))
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return _valid(candidates[0][0])
    return NOT_PROVIDED
def _extract_year(full_text: str) -> str:
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", full_text)
    if years:
        try:
            return str(max(int(y) for y in years))
        except Exception:
            return years[0]
    return NOT_PROVIDED
# ----------------------------------
# DETAIL EXTRACTION
# ----------------------------------
def extract_details(text: str) -> dict:
    """
    Extracts all certificate fields from OCR text using:
      - Label-based parsing  ("Name: ...", "Course: ...", etc.)
      - Trigger-phrase parsing ("This certifies that ...")
      - Structural regex     (degree names, date formats, cert IDs)
    Returns "Unknown" only when a field truly cannot be determined.
    """
    raw = text or ""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    full_text = " ".join(lines)       # Single line — better for label regex
    full_text_nl = "\n".join(lines)   # With newlines — better for context
    name       = _extract_name(lines, full_text)
    course     = _extract_course(lines, full_text)
    date       = _extract_date(full_text)
    cert_id    = _extract_cert_id(full_text)
    university = _extract_university(lines)
    year       = _extract_year(full_text)
    # Use year as date fallback when no formatted date was found
    if date == "Unknown" and year != "Unknown":
        date = year
    logger.info(
        "\n%s\nEXTRACTED DETAILS\n"
        "  Name       : %s\n"
        "  Course     : %s\n"
        "  Date       : %s\n"
        "  Cert ID    : %s\n"
        "  University : %s\n"
        "  Year       : %s\n%s",
        "=" * 50, name, course, date, cert_id, university, year, "=" * 50,
    )
    return {
        "name": name,
        "course": course,
        "university": university,
        "year": year,
        "date": date,
        "cert_id": cert_id,
        "full_text": full_text_nl,
    }
# ----------------------------------
# HASH / BLOCKCHAIN  (unchanged)
# ----------------------------------
def generate_hash(details):
    data_string = (
        (details.get("name") or "Unknown") + "|" +
        (details.get("course") or "Unknown") + "|" +
        (details.get("university") or "Unknown") + "|" +
        (details.get("date") or "Unknown") + "|" +
        (details.get("cert_id") or "Unknown")
    )
    cert_hash = hashlib.sha256(data_string.encode()).hexdigest()
    logger.info("Generated Hash: %s", cert_hash)
    return cert_hash
def load_hashes():
    if not os.path.exists(BLOCKCHAIN_FILE):
        return set()
    with open(BLOCKCHAIN_FILE, "r") as f:
        return set(f.read().splitlines())
def add_certificate(cert_hash):
    hashes = load_hashes()
    if cert_hash in hashes:
        return "ALREADY EXISTS"
    with open(BLOCKCHAIN_FILE, "a") as f:
        f.write(cert_hash + "\n")
    return "ISSUED SUCCESSFULLY"
def verify_certificate(cert_hash):
    hashes = load_hashes()
    return "VERIFIED" if cert_hash in hashes else "FAKE"
# ----------------------------------
# ROUTES
# ----------------------------------
@app.route("/")
def home():
    return render_template("index.html")
@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        if not _is_valid_admin_key(_admin_key_from_request()):
            return render_template("issue.html", error=_admin_key_error_message()), 403
        file = request.files.get("certificate")
        if not file or not allowed_file(file.filename):
            return render_template("issue.html", error="Invalid file type."), 400
        filepath = _save_uploaded_file(file)
        text = perform_ocr(filepath)
        details = extract_details(text)
        cert_hash = generate_hash(details)
        status = add_certificate(cert_hash)
        return render_template(
            "result.html",
            status=status,
            name=details["name"],
            course=details["course"],
            date=details["date"],
            cert_id=details["cert_id"],
            hash=cert_hash,
        )
    # GET /issue renders the issue form (issue.html already exists as a
    # template -- it is used above for the POST error path).
    return render_template("issue.html")
@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        file = request.files.get("certificate")
        if not file or not allowed_file(file.filename):
            return render_template("verify.html", error="Invalid file type."), 400
        filepath = _save_uploaded_file(file)
        text = perform_ocr(filepath)
        details = extract_details(text)
        cert_hash = generate_hash(details)
        status = verify_certificate(cert_hash)
        return render_template(
            "result.html",
            status=status,
            name=details["name"],
            course=details["course"],
            date=details["date"],
            cert_id=details["cert_id"],
            hash=cert_hash,
        )
    # GET /verify renders the verify form (verify.html already exists as a
    # template -- it is used above for the POST error path).
    return render_template("verify.html")
# ----------------------------------
# JSON API ENDPOINTS  (unchanged)
# ----------------------------------
def _process_upload(file):
    """Save uploaded file, run OCR, extract details and hash. Returns (details, cert_hash) or raises."""
    filepath = _save_uploaded_file(file)
    text = perform_ocr(filepath)
    details = extract_details(text)
    cert_hash = generate_hash(details)
    return details, cert_hash
def _details_to_api(details, cert_hash):
    """Convert extracted details dict to API response dict."""
    date_val = details.get("date", "Unknown")
    if date_val == "Unknown":
        date_val = details.get("year", "Unknown")
    cert_id = details.get("cert_id", "Unknown")
    if cert_id == "Unknown":
        cert_id = "CERT-" + cert_hash[:9].upper()
    return {
        "name": details.get("name", "Unknown"),
        "course": details.get("course", "Unknown"),
        "date": date_val,
        "cert_id": cert_id,
        "university": details.get("university", "Unknown"),
        "hash": cert_hash,
    }
@app.route("/api/issue", methods=["POST"])
@csrf.exempt
def api_issue():
    if not _is_valid_admin_key(_admin_key_from_request()):
        return jsonify({"error": _admin_key_error_message()}), 403
    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
    try:
        details, cert_hash = _process_upload(file)
        status = add_certificate(cert_hash)
        resp = _details_to_api(details, cert_hash)
        resp["status"] = status
        return jsonify(resp)
    except Exception as e:
        logger.error("api_issue error: %s", e, exc_info=True)
        error_msg = str(e) if IS_DEVELOPMENT else "Internal server error"
        return jsonify({"error": error_msg}), 500
@app.route("/api/verify", methods=["POST"])
@csrf.exempt
def api_verify():
    file = request.files.get("certificate")
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400
    try:
        details, cert_hash = _process_upload(file)
        status = verify_certificate(cert_hash)
        resp = _details_to_api(details, cert_hash)
        resp["status"] = status
        return jsonify(resp)
    except Exception as e:
        logger.error("api_verify error: %s", e, exc_info=True)
        error_msg = str(e) if IS_DEVELOPMENT else "Internal server error"
        return jsonify({"error": error_msg}), 500
# ----------------------------------
# ERROR HANDLERS
# ----------------------------------
# templates/errors/{400,403,404,429,500,503}.html were not present in the
# project as reviewed, so render_template() for them would raise
# TemplateNotFound *while already handling an error* -- turning e.g. a
# simple 404 into an unhandled 500. _render_error_page() guards against that
# by falling back to a minimal inline HTML response if the template is
# missing, so an HTML error response is always returned successfully.
from jinja2 import TemplateNotFound
def _wants_json() -> bool:
    return request.path.startswith("/api/")
def _render_error_page(template_name: str, status_code: int, message: str):
    try:
        return render_template(template_name), status_code
    except TemplateNotFound:
        logger.debug("Error template %s not found; using fallback response.", template_name)
        return (
            f"<!doctype html><title>{status_code}</title>"
            f"<h1>{status_code}</h1><p>{message}</p>"
        ), status_code
@app.errorhandler(400)
def bad_request(e):
    if _wants_json():
        return jsonify({"error": "Bad request"}), 400
    return _render_error_page("errors/400.html", 400, "Bad request.")
@app.errorhandler(403)
def forbidden(e):
    if _wants_json():
        return jsonify({"error": "Forbidden"}), 403
    return _render_error_page("errors/403.html", 403, "Forbidden.")
@app.errorhandler(404)
def not_found(e):
    if _wants_json():
        return jsonify({"error": "Not found"}), 404
    return _render_error_page("errors/404.html", 404, "Not found.")
@app.errorhandler(429)
def rate_limited(e):
    if _wants_json():
        return jsonify({"error": "Too many requests"}), 429
    return _render_error_page("errors/429.html", 429, "Too many requests.")
@app.errorhandler(500)
def server_error(e):
    if _wants_json():
        return jsonify({"error": "Internal server error"}), 500
    return _render_error_page("errors/500.html", 500, "Internal server error.")
@app.errorhandler(503)
def service_unavailable(e):
    if _wants_json():
        return jsonify({"error": "Service unavailable"}), 503
    return _render_error_page("errors/503.html", 503, "Service unavailable.")
@app.errorhandler(CSRFError)
def csrf_error(e):
    if _wants_json():
        return jsonify({"error": "CSRF validation failed"}), 400
    return _render_error_page("errors/400.html", 400, "CSRF validation failed.")
# ----------------------------------
# RUN APP
# ----------------------------------
if __name__ == "__main__":
    # Debug mode is driven by FLASK_ENV, defaulting to OFF. The Werkzeug
    # debugger (arbitrary code execution) and auto-reload are only enabled
    # when a developer explicitly opts in with FLASK_ENV=development.
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=IS_DEVELOPMENT, host=host, port=port)
