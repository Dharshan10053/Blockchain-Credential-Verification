import sys
from types import SimpleNamespace

from models import ocr


def test_pdf_ocr_keeps_page_text_separate(monkeypatch):
    pages = [object(), object()]
    monkeypatch.setitem(
        sys.modules,
        "pdf2image",
        SimpleNamespace(convert_from_path=lambda _path: pages),
    )
    monkeypatch.setattr(
        ocr, "pytesseract", SimpleNamespace(image_to_string=lambda page: {
            pages[0]: "Priya Sharma",
            pages[1]: "Advanced Data Analytics",
        }[page])
    )

    assert ocr.extract_text("certificate.pdf") == (
        "Priya Sharma\nAdvanced Data Analytics"
    )
