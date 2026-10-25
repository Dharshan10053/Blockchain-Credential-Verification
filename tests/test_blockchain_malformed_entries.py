from backend.utils.blockchain import Blockchain
from backend.utils.verification import classify_status


def test_verification_ignores_malformed_certificate_hash_values(tmp_path):
    blockchain = Blockchain(
        str(tmp_path / "blockchain.json"),
        legacy_path=str(tmp_path / "missing.txt"),
    )
    blockchain.add_block({"hash": ["not", "a", "hash"]})
    blockchain.add_block({"hash": None})

    result = classify_status("unregistered-hash", 80, blockchain)

    assert result["status"] == "FAKE"
    assert blockchain.find_all_hashes() == set()
