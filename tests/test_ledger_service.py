from services.ledger_service import LedgerService


def test_corrupt_ledger_is_not_overwritten_by_store(tmp_path):
    ledger_path = tmp_path / "ledger.json"
    ledger = LedgerService(str(ledger_path))
    corrupted_contents = "{invalid json"
    ledger_path.write_text(corrupted_contents)

    assert not ledger.store_certificate("CERT-1", "a" * 64)
    assert ledger_path.read_text() == corrupted_contents
