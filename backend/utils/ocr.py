"""
OCR extraction — supports PNG, JPG, PDF, DOCX.
Returns a single plain-text string.
"""
from __future__ import annotations
import logging
import os

logger = logging.getLogger(__name__)


def extract_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()

    if ext in (".png", ".jpg", ".jpeg"):
        return _ocr_image(filepath)
    if ext == ".pdf":
        return _ocr_pdf(filepath)
    if ext == ".docx":
        return _ocr_docx(filepath)

    raise ValueError(f"Unsupported file type: {ext}")


# ── Image ─────────────────────────────────────────────────────────────────────

def _ocr_image(filepath: str) -> str:
    import pytesseract
    from PIL import Image

    img = Image.open(filepath)
    # Pre-process: convert to greyscale, increase DPI hint
    img = img.convert("L")
    text = pytesseract.image_to_string(img, config="--oem 3 --psm 6")
    logger.debug("OCR image extracted %d chars", len(text))
    return text


# ── PDF ───────────────────────────────────────────────────────────────────────

def _ocr_pdf(filepath: str) -> str:
    """Try embedded text first; fall back to raster OCR."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        pages_text = [page.get_text() for page in doc]
        text = "\n".join(pages_text).strip()
        doc.close()
        if len(text) > 50:
            logger.debug("PDF embedded text: %d chars", len(text))
            return text
    except Exception as e:
        logger.warning("PyMuPDF failed: %s", e)

    # Raster fallback
    try:
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(filepath, dpi=200)
        text = "\n".join(pytesseract.image_to_string(img.convert("L")) for img in images)
        logger.debug("PDF raster OCR: %d chars", len(text))
        return text
    except Exception as e:
        logger.error("PDF OCR fallback failed: %s", e)
        raise


# ── DOCX ──────────────────────────────────────────────────────────────────────

def _ocr_docx(filepath: str) -> str:
    from docx import Document
    doc = Document(filepath)
    text = "\n".join(p.text for p in doc.paragraphs)
    logger.debug("DOCX extracted %d chars", len(text))
    return text
