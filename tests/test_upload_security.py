import io
from pathlib import Path

import fitz
from PIL import Image
import pytest
from werkzeug.datastructures import FileStorage

from app import MAX_IMAGE_PIXELS, MAX_PDF_PAGES, _ocr_pdf, _upload_content_is_valid


_SAMPLE_IMAGE = Path(__file__).resolve().parents[1] / "test_images" / "sample.png"


def _file_storage(data, filename):
    return FileStorage(stream=io.BytesIO(data), filename=filename)


def test_upload_image_bytes_must_match_extension():
    image_bytes = _SAMPLE_IMAGE.read_bytes()

    assert _upload_content_is_valid(_file_storage(image_bytes, "certificate.jpg"))
    assert not _upload_content_is_valid(
        _file_storage(b"not an image", "certificate.jpg")
    )
    assert not _upload_content_is_valid(
        _file_storage(image_bytes, "certificate.png")
    )


def test_pdf_upload_requires_pdf_signature():
    document = fitz.open()
    document.new_page()
    pdf_bytes = document.tobytes()
    document.close()

    assert _upload_content_is_valid(_file_storage(pdf_bytes, "certificate.pdf"))
    assert not _upload_content_is_valid(
        _file_storage(b"not a PDF", "certificate.pdf")
    )


def test_oversized_image_dimensions_are_rejected():
    image_stream = io.BytesIO()
    Image.new("RGB", (4500, 4500)).save(image_stream, format="JPEG")

    assert 4500 * 4500 > MAX_IMAGE_PIXELS
    assert not _upload_content_is_valid(
        _file_storage(image_stream.getvalue(), "oversized.jpg")
    )


def test_pdf_ocr_rejects_excessive_page_count(tmp_path):
    pdf_path = tmp_path / "too-many-pages.pdf"
    document = fitz.open()
    for _ in range(MAX_PDF_PAGES + 1):
        document.new_page()
    document.save(pdf_path)
    document.close()

    with pytest.raises(ValueError, match="page upload limit"):
        _ocr_pdf(str(pdf_path))
