from pathlib import Path

from backend.utils import report_generator


def test_report_generates_when_hash_contains_xml_markup(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "_REPORT_DIR", str(tmp_path / "reports"))

    report_path = report_generator.generate_report(
        {"hash": "legacy&hash", "status": "FAKE"}
    )

    assert report_path
    try:
        assert Path(report_path).read_bytes().startswith(b"%PDF-")
    finally:
        Path(report_path).unlink(missing_ok=True)
