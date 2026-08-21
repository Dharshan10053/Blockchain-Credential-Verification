"""
Regression tests for certificate field extraction (app.extract_details and
friends).

These use synthetic OCR text (not real image files) so they run fast and
without OCR/Tesseract/Poppler installed. The synthetic text is written to
resemble what pytesseract would actually emit for the layouts described --
line-by-line, ragged, no fixed columns -- rather than hand-crafting a single
perfect input.

Run with:  python3 -m pytest tests/test_extraction.py -v
       or:  python3 tests/test_extraction.py
"""
import shutil
import os
import sys

os.environ.setdefault("FLASK_ENV", "development")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import extract_details, perform_ocr  # noqa: E402

_FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
_REAL_CERT_PATH = os.path.join(_FIXTURE_DIR, "Intro_to_Python_Certificate.jpg")
_FORAGE_CERT_PATH = os.path.join(_FIXTURE_DIR, "Forage_Data_Analytics_Certificate.png")
_TESSERACT_AVAILABLE = shutil.which("tesseract") is not None


def test_real_forage_certificate_end_to_end():
    """
    End-to-end regression test using the ACTUAL Forage/Accenture certificate
    image reported as failing, through the real perform_ocr() ->
    extract_details() pipeline. Requires tesseract to be installed; skipped
    otherwise. OCR character-level noise (e.g. a misread character inside
    the verification code) is tolerated -- what this test guards against is
    the field-mapping bugs: wrong field (course), missing field (issuer),
    and structurally wrong value (verification code from a lost OCR line).
    """
    if not _TESSERACT_AVAILABLE:
        print("SKIP: tesseract not installed, cannot run real OCR test.")
        return
    if not os.path.exists(_FORAGE_CERT_PATH):
        print(f"SKIP: fixture not found at {_FORAGE_CERT_PATH}.")
        return

    raw_text = perform_ocr(_FORAGE_CERT_PATH)
    details = extract_details(raw_text)

    assert details["name"] == "KADARI JAYANTH", details
    assert details["course"] == "Data Analytics and Visualization Job Simulation", details
    assert details["university"] == "Forage", details
    assert details["cert_id"] == "baufGddHyZpSw9moj", details


def test_real_learntube_certificate_end_to_end():
    """
    End-to-end regression test using the ACTUAL certificate image (not
    synthetic OCR text) through the real perform_ocr() -> extract_details()
    pipeline. Requires tesseract to be installed; skipped otherwise.
    """
    if not _TESSERACT_AVAILABLE:
        print("SKIP: tesseract not installed, cannot run real OCR test.")
        return
    if not os.path.exists(_REAL_CERT_PATH):
        print(f"SKIP: fixture not found at {_REAL_CERT_PATH}.")
        return

    raw_text = perform_ocr(_REAL_CERT_PATH)
    assert "Intro To Python" in raw_text, f"OCR raw text missing course title: {raw_text!r}"
    assert "Jayanth" in raw_text, f"OCR raw text missing candidate name: {raw_text!r}"

    details = extract_details(raw_text)
    assert details["name"] == "Jayanth", details
    assert details["course"] == "Intro To Python", details
    assert details["cert_id"] == "Int15762022233437", details
    assert details["date"] == "10/18/2022", details


def test_learntube_careerninja_bug_regression():
    """
    Regression test for the reported bug: course was extracted as the
    "»» LearnTube by CareerNinja" branding line instead of "Intro To Python".

    This reconstructs the raw-OCR-like text for that certificate layout
    (branding line above the "Certificate of Completion" heading, real
    course title introduced later by a completion trigger phrase and
    also quoted).
    """
    raw_text = (
        "»» LearnTube\n"
        "by CareerNinja\n"
        "CERTIFICATE OF COMPLETION\n"
        "This is to certify that\n"
        "Jayanth\n"
        "has successfully completed the course\n"
        "\"Intro To Python\"\n"
        "Certificate ID: Int15762022233437\n"
        "Date: 10/18/2022\n"
        "Shronit Lad\n"
        "Founder, CareerNinja\n"
    )
    details = extract_details(raw_text)

    assert details["course"] == "Intro To Python", details
    assert details["name"] == "Jayanth", details
    assert details["cert_id"] == "Int15762022233437", details
    assert details["date"] == "10/18/2022", details
    # The branding text must not leak into the course field.
    assert "LearnTube" not in details["course"]
    assert "CareerNinja" not in details["course"]


def test_university_degree_layout_still_works():
    """
    A completely different, more traditional layout (no branding line, no
    quotes) should still resolve correctly via the degree-pattern /
    trigger-phrase signals -- confirms the fix isn't specific to one
    certificate design.
    """
    raw_text = (
        "XYZ UNIVERSITY\n"
        "CERTIFICATE OF COMPLETION\n"
        "This certificate is proudly presented to\n"
        "John Smith\n"
        "for successfully completing\n"
        "Bachelor of Computer Science\n"
        "Certificate No: CERT-2023-00456\n"
        "Date: March 4, 2023\n"
    )
    details = extract_details(raw_text)

    assert "Bachelor of Computer Science" in details["course"], details
    assert details["name"] == "John Smith", details
    assert details["cert_id"] == "CERT-2023-00456", details
    assert "2023" in details["date"], details


def test_label_based_course_layout():
    """
    A layout that explicitly labels the course field should use that label
    directly rather than any positional heuristic.
    """
    raw_text = (
        "ACME TRAINING ACADEMY\n"
        "Certificate of Achievement\n"
        "Awarded to: Priya Sharma\n"
        "Course: Advanced Data Structures\n"
        "Certificate ID: ACME-88213\n"
        "Issued on: 2024-05-01\n"
    )
    details = extract_details(raw_text)

    assert details["course"] == "Advanced Data Structures", details
    assert details["name"] == "Priya Sharma", details


def test_forage_task_list_layout_not_confused_with_course():
    """
    Regression test for the reported bug: on the Forage/Accenture "Data
    Analytics and Visualization Job Simulation" certificate, the course was
    extracted as "Project Understanding" (the first item in a bulleted task
    list) instead of the real title, which sits directly under the
    recipient's name and above the "Certificate of Completion" heading.

    Root cause: the generic trigger phrase "has completed" matched inside
    "... has completed practical tasks in:" -- a sentence that introduces a
    *list*, not a single title -- so the task-list items that followed were
    scored as strong course-title candidates. This reconstructs the
    raw-OCR-like text for that layout (title wrapped across two lines,
    list-introducing sentence ending in ":", followed by task names).
    """
    raw_text = (
        "accenture\n"
        "Forage\n"
        "KADARI JAYANTH\n"
        "Data Analytics and Visualization Job\n"
        "Simulation\n"
        "Certificate of Completion\n"
        "July 30th, 2024\n"
        "Over the period of July 2024, KADARI JAYANTH has completed practical tasks in:\n"
        "Project Understanding\n"
        "Data Cleaning & Modeling\n"
        "Data Visualization & Storytelling\n"
        "Present to the Client\n"
        "Caroline Dudley Tom Brunskill\n"
        "Managing Director CEO, Co-Founder of\n"
        "North America Forage\n"
        "Recruiting\n"
        "Enrolment Verification Code baufGddHyZpSw9moj | "
        "User Verification Code sWmCHJ6ybQdnNZzv6 | Issued by Forage\n"
    )
    details = extract_details(raw_text)

    assert details["name"] == "KADARI JAYANTH", details
    assert details["course"] == "Data Analytics and Visualization Job Simulation", details
    # None of the task-list items should ever win as the course title.
    for task in ("Project Understanding", "Data Cleaning & Modeling",
                 "Data Visualization & Storytelling", "Present to the Client"):
        assert details["course"] != task, details
    assert details["university"] == "Forage", details
    assert details["cert_id"] == "baufGddHyZpSw9moj", details


def test_list_intro_trigger_line_is_not_used_as_course_source():
    """
    Narrower unit-level check: a sentence ending in ":" that happens to
    contain "has completed" must not be treated as a course-introducing
    trigger, even when there is no other course signal in the document.
    Extraction should fall back to "Not Provided" rather than guessing a
    list item.
    """
    raw_text = (
        "Jordan Lee has completed practical tasks in:\n"
        "Task One\n"
        "Task Two\n"
        "Task Three\n"
    )
    details = extract_details(raw_text)
    assert details["course"] == "Not Provided", details
    assert details["course"] not in ("Task One", "Task Two", "Task Three")


def test_branding_only_candidate_is_rejected_not_fabricated():
    """
    If the only text near the heading is branding-like and there is no
    other course signal anywhere in the document, extraction should report
    the field as unavailable rather than returning the branding text.
    """
    raw_text = (
        "»» SomePlatform by SomeCompany\n"
        "CERTIFICATE OF COMPLETION\n"
        "This is to certify that\n"
        "Alex Doe\n"
    )
    details = extract_details(raw_text)

    assert details["course"] == "Not Provided", details
    assert "SomePlatform" not in details["course"]
    assert "SomeCompany" not in details["course"]


if __name__ == "__main__":
    tests = [
        test_real_learntube_certificate_end_to_end,
        test_real_forage_certificate_end_to_end,
        test_learntube_careerninja_bug_regression,
        test_university_degree_layout_still_works,
        test_label_based_course_layout,
        test_forage_task_list_layout_not_confused_with_course,
        test_list_intro_trigger_line_is_not_used_as_course_source,
        test_branding_only_candidate_is_rejected_not_fabricated,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__}: {e}")
    if failures:
        print(f"\n{failures} test(s) failed.")
        sys.exit(1)
    print("\nAll tests passed.")