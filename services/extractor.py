import os
import json
import logging
import re
import tempfile
import shutil
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

GENAI_MODELS = [
    os.getenv("GEMINI_MODEL", "").strip(),
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
]

GENERIC_TITLES = {
    "certificate",
    "certificate of completion",
    "completion",
    "achievement",
    "award",
    "certificate awarded",
    "certificate of achievement",
}

DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}\b",
    r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
]

ID_LABEL_PATTERNS = [
    r"certificate\s*id[:\s#-]*([A-Z0-9\-_/]+)",
    r"cert\s*id[:\s#-]*([A-Z0-9\-_/]+)",
    r"credential\s*id[:\s#-]*([A-Z0-9\-_/]+)",
    r"registration\s*no[:\s#-]*([A-Z0-9\-_/]+)",
    r"certificate\s*no[:\s#-]*([A-Z0-9\-_/]+)",
    r"\bid[:\s#-]*([A-Z0-9\-_/]+)",
]


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _looks_like_generic_title(value: Optional[str]) -> bool:
    if not value:
        return True
    return value.strip().lower() in GENERIC_TITLES


def _derive_certificate_id(data: Dict[str, Any]) -> str:
    base = " | ".join(
        _clean_text(data.get(k)) or ""
        for k in ("name", "certificate_title", "issuer", "date")
    ).strip().lower()

    if not base:
        base = "unknown-certificate"

    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:10].upper()
    return f"CERT-{digest}"


def _calculate_extraction_confidence(payload: Dict[str, Any], is_ocr: bool) -> float:
    score = 100.0
    if not payload.get("name") or payload["name"].strip() == "Not Provided":
        score -= 25.0
    if not payload.get("certificate_title") or payload["certificate_title"].strip() == "Not Provided":
        score -= 20.0
    if not payload.get("issuer") or payload["issuer"].strip() == "Not Provided":
        score -= 15.0
    if not payload.get("certificate_id") or payload["certificate_id"].startswith("CERT-"):
        score -= 15.0
    if not payload.get("date") or payload["date"].strip() == "Not Provided":
        score -= 10.0
    
    if is_ocr and score > 80.0:
        score = 80.0
    return max(0.0, round(score, 1))


def _finalize_payload(data: Dict[str, Any], is_ocr: bool = False) -> Dict[str, Any]:
    # Support backward compatibility for 'issuer' and 'organization' mapped to 'issuing_authority'
    extracted_authority = data.get("issuing_authority") or data.get("issuer") or data.get("organization")
    
    payload = {
        "name": _clean_text(data.get("name")),
        "certificate_title": _clean_text(data.get("certificate_title")),
        "issuing_authority": _clean_text(extracted_authority),
        "issuer": _clean_text(extracted_authority), # Legacy fallback
        "date": _clean_text(data.get("date")),
        "certificate_id": _clean_text(data.get("certificate_id")),
    }

    if _looks_like_generic_title(payload["certificate_title"]):
        payload["certificate_title"] = None

    # Cleanup issuer/issuing_authority if the model returned a long line with commas.
    if payload["issuing_authority"] and "," in payload["issuing_authority"]:
        parts = [p.strip() for p in payload["issuing_authority"].split(",") if p.strip()]
        if parts:
            payload["issuing_authority"] = parts[-1]
            payload["issuer"] = parts[-1]

    if not payload["certificate_id"]:
        payload["certificate_id"] = _derive_certificate_id(payload)

    # Use issuing_authority for confidence scoring
    # Calculate confidence based on new payload
    score = 100.0
    if not payload.get("name") or payload["name"] == "Not Provided":
        score -= 25.0
    if not payload.get("certificate_title") or payload["certificate_title"] == "Not Provided":
        score -= 20.0
    if not payload.get("issuing_authority") or payload["issuing_authority"] == "Not Provided":
        score -= 15.0
    if not payload.get("certificate_id") or payload["certificate_id"].startswith("CERT-"):
        score -= 15.0
    if not payload.get("date") or payload["date"] == "Not Provided":
        score -= 10.0
    
    if is_ocr and score > 80.0:
        score = 80.0
    
    payload["confidence_score"] = max(0.0, round(score, 1))
    
    if "raw_ocr_issuer" in data:
        payload["raw_ocr_issuer"] = data["raw_ocr_issuer"]
        
    return payload


def _image_to_bytes(filepath: str) -> bytes:
    with Image.open(filepath) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()


def _pdf_or_docx_to_bytes(filepath: str) -> Tuple[bytes, str]:
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return path.read_bytes(), "application/pdf"

    if ext == ".docx":
        tmp_dir = tempfile.mkdtemp(prefix="certauth_docx_")
        try:
            from docx2pdf import convert as docx2pdf_convert

            pdf_path = Path(tmp_dir) / f"{path.stem}.pdf"
            try:
                docx2pdf_convert(str(path), str(pdf_path))
            except Exception as e:
                logger.error(f"docx2pdf conversion failed, unsupported on this server: {e}")
                raise ValueError("docx2pdf conversion is unsupported on this server. Please upload a PDF or image instead.")
            return pdf_path.read_bytes(), "application/pdf"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    raise ValueError(f"Unsupported file type for document conversion: {ext}")


def _build_media_part(filepath: str) -> types.Part:
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext in ALLOWED_IMAGE_EXTS:
        mime_type = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
        return types.Part.from_bytes(
            data=path.read_bytes(),
            mime_type=mime_type,
        )

    if ext in {".pdf", ".docx"}:
        data, mime_type = _pdf_or_docx_to_bytes(filepath)
        return types.Part.from_bytes(data=data, mime_type=mime_type)

    raise ValueError(f"Unsupported file type: {ext}")


def _pick_models() -> List[str]:
    models = [m for m in GENAI_MODELS if m]
    if not models:
        models = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3-flash-preview"]
    return models


def _parse_json_from_text(text: str) -> Dict[str, Any]:
    cleaned = re.sub(r"```json|```", "", text or "").strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("No JSON found in model response")
    return json.loads(match.group(0))


def _ocr_text_from_images(images: List[Image.Image]) -> str:
    texts: List[str] = []

    # Try EasyOCR first if it is installed and working.
    try:
        import easyocr
        import numpy as np

        reader = easyocr.Reader(["en"], gpu=False)
        for img in images:
            arr = np.array(img.convert("RGB"))
            chunks = reader.readtext(arr, detail=0, paragraph=True)
            if chunks:
                texts.append("\n".join(chunks))
    except Exception:
        pass

    # Fallback to Tesseract.
    if not texts:
        try:
            import pytesseract
            
            if os.name == 'nt':
                pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

            for img in images:
                texts.append(pytesseract.image_to_string(img.convert("RGB")))
        except Exception as exc:
            raise ValueError("OCR fallback unavailable. Install easyocr or pytesseract.") from exc

    return "\n".join(t for t in texts if t and t.strip())


def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    from PIL import ImageOps, ImageEnhance
    
    img = ImageOps.grayscale(img)
    
    if img.width < 1200:
        new_width = 1600
        new_height = int((new_width / img.width) * img.height)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    return img


def _file_to_ocr_images(filepath: str) -> List[Image.Image]:
    path = Path(filepath)
    ext = path.suffix.lower()

    images = []
    if ext in ALLOWED_IMAGE_EXTS:
        images = [Image.open(filepath).convert("RGB")]
    elif ext == ".pdf":
        from pdf2image import convert_from_path
        images = [img.convert("RGB") for img in convert_from_path(filepath, dpi=220, first_page=1, last_page=1)]
    elif ext == ".docx":
        tmp_dir = tempfile.mkdtemp(prefix="certauth_docx_")
        try:
            from docx2pdf import convert as docx2pdf_convert
            from pdf2image import convert_from_path

            pdf_path = Path(tmp_dir) / f"{path.stem}.pdf"
            try:
                docx2pdf_convert(str(path), str(pdf_path))
            except Exception as e:
                logger.error(f"docx2pdf conversion failed: {e}")
                raise ValueError("docx2pdf conversion is unsupported on this server. Please upload a PDF or image instead.")
            images = [img.convert("RGB") for img in convert_from_path(str(pdf_path), dpi=220, first_page=1, last_page=1)]
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        raise ValueError(f"Unsupported file type for OCR: {ext}")
        
    return [_preprocess_for_ocr(img) for img in images]


def _extract_from_text(text: str) -> Dict[str, Any]:
    raw_lines = [re.sub(r"\s+", " ", ln).strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in raw_lines if ln]
    joined = "\n".join(lines)

    # Date
    date = None
    for pat in DATE_PATTERNS:
        m = re.search(pat, joined, re.I)
        if m:
            date = m.group(0)
            break

    # Certificate ID
    cert_id = None
    for pat in ID_LABEL_PATTERNS:
        m = re.search(pat, joined, re.I)
        if m:
            cert_id = m.group(1).strip()
            break

    if not cert_id:
        tokens = re.findall(r"\b[A-Z0-9][A-Z0-9\-_./]{6,}\b", joined, re.I)
        bad = {"certificate", "completion", "achievement", "course", "title", "issuer"}
        for tok in tokens:
            if tok.lower() not in bad and not re.fullmatch(r"\d{1,4}", tok):
                cert_id = tok
                break

    # Name
    name = None
    for pat in [
        r"(?:this is to certify that|certify that|awarded to|presented to|issued to|conferred upon|proudly presented to)\s+(.+)",
    ]:
        m = re.search(pat, joined, re.I)
        if m:
            candidate = _clean_text(m.group(1))
            if candidate:
                name = candidate.split("\n")[0].strip(" ,;:-")
                break

    if not name:
        # Assume the name is one of the prominent center lines (2-4 words)
        candidate_lines = []
        for ln in lines[1:len(lines)-2]: # skip very top and bottom
            low = ln.lower()
            if any(k in low for k in ["certificate", "completion", "award", "issuer", "signed", "authority", "date", "id"]):
                continue
            words = ln.split()
            if 2 <= len(words) <= 4 and all(w[:1].isupper() for w in words if w.isalpha()):
                candidate_lines.append(ln)
        if candidate_lines:
            name = candidate_lines[0]

    # Title
    title = None
    for pat in [
        r"(?:for successfully completing|awarded for|certification in|course|title|program|subject)\s*[:\-]?\s*(.+)",
    ]:
        m = re.search(pat, joined, re.I)
        if m:
            title = _clean_text(m.group(1).split("\n")[0])
            if title:
                break

    if not title:
        for ln in lines:
            if not _looks_like_generic_title(ln) and 10 < len(ln) < 80:
                # Exclude if it looks like a name or date
                if not re.search(r"\d", ln) and "certify" not in ln.lower():
                    title = ln
                    break

    if _looks_like_generic_title(title):
        title = None

    # Issuing Authority (Scoring-based Hybrid Extraction)
    issuing_authority = None
    raw_ocr_issuer = None
    issuer_keywords = [
        "university", "academy", "institute", "organization", "company", "inc", "llc", "ltd",
        "issued by", "authorized by", "board", "certification authority", "school", "college"
    ]
    
    # Scoring each line for issuer probability
    best_issuer_score = -1
    best_issuer_candidate = None
    
    import difflib
    for i, ln in enumerate(lines):
        score = 0
        low = ln.lower()
        
        # Positional weighting (Top 3 or Bottom 4 lines are highly likely)
        if i < 3 or i >= len(lines) - 4:
            score += 3
            
        # Keyword scoring
        for kw in issuer_keywords:
            if kw in low:
                score += 5
                
        # Uppercase density (Institutions are often fully capitalized or title case)
        uppers = sum(1 for c in ln if c.isupper())
        if len(ln) > 0 and uppers / len(ln) > 0.5:
            score += 2
            
        # Layout-aware (near signatures)
        if i < len(lines) - 1:
            next_low = lines[i+1].lower()
            if any(title in next_low for title in ["founder", "ceo", "director", "instructor", "president", "chair"]):
                score += 8
                
        # Penalties
        if name and ln.lower() == name.lower():
            score -= 20
        if title and ln.lower() == title.lower():
            score -= 20
        if "certify" in low or "completed" in low or "awarded" in low or "certificate" in low:
            score -= 5
            
        # Fuzzy OCR correction support (identifying broken institutional names)
        # E.g., 'Un1vers1ty'
        for kw in ["university", "institute", "academy", "board", "organization"]:
            for word in low.split():
                if difflib.SequenceMatcher(None, kw, word).ratio() > 0.8:
                    score += 4
                    break
        
        if score > best_issuer_score and score > 0:
            best_issuer_score = score
            best_issuer_candidate = ln
            
    if best_issuer_candidate:
        issuing_authority = best_issuer_candidate
        raw_ocr_issuer = best_issuer_candidate

    result = {
        "name": name,
        "certificate_title": title,
        "issuing_authority": issuing_authority,
        "raw_ocr_issuer": raw_ocr_issuer,
        "date": date,
        "certificate_id": cert_id,
    }
    return _finalize_payload(result, is_ocr=True)


def _extract_with_gemini(filepath: str) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)
    media_part = _build_media_part(filepath)

    prompt = """
Extract certificate data into STRICT JSON.

You are an expert document understanding AI analyzing a certificate. You must use layout context, typography prominence, and semantic relationships to correctly extract the fields, even for artistic or unconventional certificates.

Rules for Extraction:
1. **Course / Title (certificate_title)**: 
   - Look for the largest, most prominent text often centered on the page.
   - Look for text immediately following phrases like "successfully completed", "awarded for", "certification in", or "has completed the course".
   - Ignore generic headers like "Certificate of Completion" unless it's the ONLY title.
2. **Issuing Authority (issuing_authority)**:
   - Scan the very top header or the bottom footer regions.
   - Look near logos or institutional seals.
   - Look for signatures and the titles below them (e.g., if signed by "Jane Doe, CEO, TechCorp", the issuing_authority is "TechCorp").
   - Distinguish carefully between the Candidate's name and the Issuing Authority.
3. **Candidate Name (name)**:
   - Usually follows "This is to certify that", "awarded to", or "presented to".
   - Often uses a distinct, sometimes cursive, decorative font in the center.
4. **Certificate ID (certificate_id)**:
   - Scan bottom corners for alphanumeric strings near "ID", "Credential", or "No.".
5. **Date (date)**:
   - Look for dates near signatures or "Issued on".

- Use visible text exactly as shown. Do NOT guess. Preserve low-confidence text if it exists.
- If a field is missing or cannot be confidently inferred, return null. Do NOT use blank strings or "Not Extracted".
- Return ONLY a JSON object with:
  "name", "certificate_title", "issuing_authority", "date", "certificate_id", "confidence_score"
"""

    last_error = None

    for model_name in _pick_models():
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[media_part, prompt],
            )

            raw_text = (response.text or "").strip()

            parsed = _parse_json_from_text(raw_text)
            parsed = _finalize_payload(parsed, is_ocr=False)

            return parsed

        except Exception as exc:
            last_error = exc
            msg = str(exc).lower()

            if any(key in msg for key in ["429", "resource_exhausted", "quota", "404", "not found"]):
                logger.warning("Gemini unavailable/rate-limited for %s: %s", model_name, exc)
                continue

            logger.error("Gemini extraction failed: %s", exc)
            break

    if last_error:
        logger.info("Gemini extraction not used: %s", last_error)

    return None


def extract_details(filepath: str) -> Dict[str, Any]:
    # 1) Try Gemini first
    try:
        gemini_result = _extract_with_gemini(filepath)
        if gemini_result:
            return gemini_result
    except Exception as exc:
        logger.warning("Gemini path failed, switching to OCR fallback: %s", exc)

    # 2) OCR fallback
    try:
        images = _file_to_ocr_images(filepath)
        ocr_text = _ocr_text_from_images(images)
        logger.info("OCR fallback text length: %s", len(ocr_text))

        if not ocr_text.strip():
            raise ValueError("OCR fallback produced no text")

        parsed = _extract_from_text(ocr_text)
        return parsed

    except Exception as ocr_exc:
        logger.error("OCR fallback failed: %s", ocr_exc)
        raise
    def extract_details_v2_disabled(filepath: str) -> Dict[str, Any]:    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)

    prompt = """
Extract certificate data into STRICT JSON.

Rules:
- Read the layout visually if possible.
- Use visible text exactly as shown.
- Do NOT guess.
- If a field is missing, return null.
- Return only JSON with:
  name, certificate_title, issuing_authority, date, certificate_id, confidence_score
"""

    media_part = _build_media_part(filepath)

    last_error = None

    for model_name in _pick_models():
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[media_part, prompt],  # image/file first, prompt second
            )

            raw_text = (response.text or "").strip()
            print("RAW:", raw_text)

            parsed = _parse_json_from_text(raw_text)
            parsed = _finalize_payload(parsed, confidence=parsed.get("confidence_score", 0.0))

            print("PARSED:", parsed)
            return parsed

        except Exception as exc:
            last_error = exc
            msg = str(exc).lower()

            if any(key in msg for key in ["429", "resource_exhausted", "quota", "404", "not found"]):
                logger.warning("Gemini model unavailable or rate-limited for %s: %s", model_name, exc)
                continue

            logger.error("Gemini extraction failed: %s", exc)
            continue

    # Fallback: local OCR
    try:
        images = _file_to_ocr_images(filepath)
        ocr_text = _ocr_text_from_images(images)
        logger.info("OCR fallback text length: %s", len(ocr_text))

        if not ocr_text.strip():
            raise ValueError("OCR fallback produced no text")

        parsed = _extract_from_text(ocr_text)
        return parsed

    except Exception as ocr_exc:
        logger.error("OCR fallback failed: %s", ocr_exc)
        if last_error:
            raise last_error
        raise ocr_exc
