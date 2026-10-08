import app as app_module

from backend.utils.verification_confidence import calculate_verification_confidence


DETAILS = {
    "name": "Priya Sharma",
    "course": "Advanced Data Analytics",
    "university": "ACME Training Academy",
    "date": "12 March 2024",
    "year": "2024",
    "cert_id": "ACME-2024-889210",
}
WORDS = [
    {"text": word, "conf": 96}
    for value in (
        "Priya Sharma", "Advanced Data Analytics", "ACME Training Academy",
        "12 March 2024", "ACME-2024-889210",
    )
    for word in value.split()
]


def test_high_tesseract_confidence_and_complete_fields_score_high():
    result = calculate_verification_confidence(DETAILS, WORDS)

    assert result["ocr_confidence_available"] is True
    assert result["fields_found"] == result["field_count"] == 5
    assert result["confidence_score"] == 97.6
    assert all(score == 96 for score in result["field_confidence"].values())
    assert result["consistency_score"] == 100


def test_low_tesseract_confidence_and_missing_field_lower_score():
    poor_words = [{**word, "conf": 25} for word in WORDS]
    incomplete_details = {**DETAILS, "cert_id": "Not Extracted"}

    result = calculate_verification_confidence(incomplete_details, poor_words)

    assert result["fields_found"] == 4
    assert result["field_confidence"]["cert_id"] == 0
    assert result["confidence_score"] < 60
    assert result["confidence_score"] < calculate_verification_confidence(
        DETAILS, WORDS
    )["confidence_score"]


def test_unavailable_and_invalid_ocr_confidence_is_handled_safely():
    result = calculate_verification_confidence(
        DETAILS,
        [
            {"text": "Priya", "conf": "-1"},
            {"text": "Sharma", "conf": "not-a-number"},
            {"text": "", "conf": 90},
        ],
    )

    assert result["ocr_confidence_available"] is False
    assert result["field_confidence"]["name"] is None
    assert result["confidence_score"] == 75
    assert "capped at 75%" in result["formula"]


def test_date_year_conflict_reduces_consistency_and_score():
    mismatched = {**DETAILS, "year": "2023"}

    result = calculate_verification_confidence(mismatched, WORDS)

    assert result["consistency_score"] < 100
    assert any("conflict" in check for check in result["consistency_checks"])
    assert result["confidence_score"] < calculate_verification_confidence(
        DETAILS, WORDS
    )["confidence_score"]


def test_layout_ocr_uses_tesseract_word_confidence(monkeypatch):
    image = object()
    monkeypatch.setattr(app_module, "_preprocess_for_ocr", lambda source: image)
    monkeypatch.setattr(
        app_module.pytesseract,
        "image_to_data",
        lambda source, **kwargs: {
            "text": ["Priya", "Sharma", ""],
            "left": [1, 2, 0],
            "top": [3, 4, 0],
            "width": [5, 6, 0],
            "height": [7, 8, 0],
            "conf": ["91.5", "bad", "-1"],
        },
    )

    blocks = app_module._ocr_image_with_layout(object())

    assert [block["text"] for block in blocks] == ["Priya", "Sharma"]
    assert blocks[0]["conf"] == 91.5
    assert blocks[1]["conf"] == -1
