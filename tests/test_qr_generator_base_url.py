import sys
from types import SimpleNamespace

from backend.utils import qr_generator


def test_saved_qr_url_does_not_duplicate_trailing_slash(monkeypatch, tmp_path):
    captured_urls = []

    class FakeQr:
        def save(self, path):
            with open(path, "w", encoding="utf-8") as image_file:
                image_file.write("fake QR image")

    def make_qr(url):
        captured_urls.append(url)
        return FakeQr()

    monkeypatch.setattr(qr_generator, "_QR_DIR", str(tmp_path / "qrcodes"))
    monkeypatch.setitem(sys.modules, "qrcode", SimpleNamespace(make=make_qr))

    qr_generator.generate_qr("abc", "https://verify.example/")
    qr_generator.generate_qr("token", "https://verify.example///", is_token=True)

    assert captured_urls == [
        "https://verify.example/certificate/abc",
        "https://verify.example/verify_token/token",
    ]
