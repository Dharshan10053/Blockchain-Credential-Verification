import sys
from types import SimpleNamespace

from backend.utils import qr_generator


def test_saved_qr_path_is_scoped_to_verification_url(monkeypatch, tmp_path):
    class FakeQr:
        def save(self, path):
            with open(path, "w", encoding="utf-8") as image_file:
                image_file.write("fake QR image")

    monkeypatch.setattr(qr_generator, "_QR_DIR", str(tmp_path / "qrcodes"))
    monkeypatch.setitem(
        sys.modules, "qrcode", SimpleNamespace(make=lambda _url: FakeQr())
    )

    default_url_path = qr_generator.generate_qr("same-id", "https://one.example")
    other_host_path = qr_generator.generate_qr("same-id", "https://two.example")
    token_url_path = qr_generator.generate_qr(
        "same-id", "https://one.example", is_token=True
    )

    assert len({default_url_path, other_host_path, token_url_path}) == 3
