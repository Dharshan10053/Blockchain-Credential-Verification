import hashlib
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


def test_legacy_raw_string_genesis_hash_is_valid(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    legacy_path = tmp_path / "missing.txt"
    genesis = {
        "index": 0,
        "timestamp": "2026-03-03T12:12:52.018845Z",
        "data": "Genesis Block",
        "previous_hash": "0",
    }
    content = (
        f"{genesis['index']}{genesis['timestamp']}"
        f"{genesis['data']}{genesis['previous_hash']}"
    )
    genesis["hash"] = hashlib.sha256(content.encode()).hexdigest()
    chain_path.write_text(json.dumps({"chain": [genesis]}))

    assert Blockchain(str(chain_path), legacy_path=str(legacy_path)).is_valid()


def test_legacy_raw_string_hash_is_not_accepted_for_other_genesis_data(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    genesis = {
        "index": 0,
        "timestamp": "2026-03-03T12:12:52.018845Z",
        "data": "Altered Genesis Block",
        "previous_hash": "0",
    }
    content = (
        f"{genesis['index']}{genesis['timestamp']}"
        f"{genesis['data']}{genesis['previous_hash']}"
    )
    genesis["hash"] = hashlib.sha256(content.encode()).hexdigest()
    chain_path.write_text(json.dumps({"chain": [genesis]}))

    assert not Blockchain(str(chain_path), legacy_path=str(tmp_path / "missing.txt")).is_valid()


def test_timestamp_free_genesis_hash_is_not_accepted_for_other_data(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    genesis = {
        "index": 0,
        "timestamp": "2026-03-03T12:12:52.018845Z",
        "data": "Altered Genesis Block",
        "previous_hash": "0",
    }
    genesis["hash"] = Blockchain._compute_hash(
        genesis["index"], "", genesis["data"], genesis["previous_hash"]
    )
    chain_path.write_text(json.dumps({"chain": [genesis]}))

    assert not Blockchain(str(chain_path), legacy_path=str(tmp_path / "missing.txt")).is_valid()


def test_tampered_structured_chain_is_invalid(tmp_path):
    chain_path = tmp_path / "blockchain.json"
    blockchain = Blockchain(str(chain_path), legacy_path=str(tmp_path / "missing.txt"))
    blockchain.add_block({"hash": "c" * 64})

    payload = json.loads(chain_path.read_text())
    payload["chain"][1]["data"]["hash"] = "d" * 64
    chain_path.write_text(json.dumps(payload))

    assert not Blockchain(str(chain_path), legacy_path=str(tmp_path / "missing.txt")).is_valid()
