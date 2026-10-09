import os

import fitz

from backend.utils import report_generator


def test_report_renders_certificate_fields_as_text_not_reportlab_markup(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(report_generator, "_REPORT_DIR", str(tmp_path))
    malicious_name = "<b>Untrusted Holder</b>"

    report_path = report_generator.generate_report(
        {
            "hash": "a" * 64,
            "status": "FAKE",
            "label": "Unverified",
            "name": malicious_name,
        }
    )
    assert report_path
    try:
        with fitz.open(report_path) as document:
            pdf_text = "\n".join(page.get_text() for page in document)
    finally:
        os.remove(report_path)

    assert malicious_name in pdf_text
