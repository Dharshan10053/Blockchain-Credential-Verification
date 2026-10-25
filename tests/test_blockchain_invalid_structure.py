from backend.utils.blockchain import Blockchain


def test_chain_validation_returns_false_for_non_object_blocks(tmp_path):
    blockchain = Blockchain(
        str(tmp_path / "blockchain.json"),
        legacy_path=str(tmp_path / "missing.txt"),
    )
    blockchain.chain.append("malformed block")

    assert blockchain.is_valid() is False
