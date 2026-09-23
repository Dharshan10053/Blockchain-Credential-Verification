import json

from backend.utils.blockchain import Blockchain


def test_legacy_text_hashes_migrate_once_without_duplication(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    legacy_path = tmp_path / "blockchain.txt"
    first_hash = "a" * 64
    second_hash = "b" * 64
    legacy_path.write_text(f"{first_hash}\n{second_hash}\n{first_hash}\n")

    blockchain = Blockchain(str(chain_path), legacy_path=str(legacy_path))

    assert blockchain.is_valid()
    assert blockchain.find_all_hashes() == {first_hash, second_hash}
    assert len(blockchain.chain) == 3

    restarted = Blockchain(str(chain_path), legacy_path=str(legacy_path))
    assert len(restarted.chain) == 3
    assert restarted.find_all_hashes() == {first_hash, second_hash}
    assert legacy_path.read_text() == f"{first_hash}\n{second_hash}\n{first_hash}\n"


def test_tampered_structured_chain_is_invalid(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    blockchain = Blockchain(str(chain_path), legacy_path=str(tmp_path / "missing.txt"))
    blockchain.add_block({"hash": "c" * 64})

    payload = json.loads(chain_path.read_text())
    payload["chain"][1]["data"]["hash"] = "d" * 64
    chain_path.write_text(json.dumps(payload))

    assert not Blockchain(str(chain_path), legacy_path=str(tmp_path / "missing.txt")).is_valid()
