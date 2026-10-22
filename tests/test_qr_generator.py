import sys
from pathlib import Path
from types import SimpleNamespace

from backend.utils import qr_generator


def test_qr_identifier_cannot_escape_output_directory(monkeypatch, tmp_path):
    class FakeQr:
        def save(self, path):
            Path(path).write_bytes(b"qr")

    output_dir = tmp_path / "qrcodes"
    monkeypatch.setattr(qr_generator, "_QR_DIR", str(output_dir))
    monkeypatch.setitem(
        sys.modules,
        "qrcode",
        SimpleNamespace(make=lambda _url: FakeQr()),
    )

    output_path = Path(qr_generator.generate_qr("../../outside/file"))

    assert output_path.parent == output_dir
    assert output_path.read_bytes() == b"qr"
