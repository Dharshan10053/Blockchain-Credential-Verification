"""
Blockchain module for certificate authenticity.

Persists the chain to blockchain.json and loads it on startup.
Provides block structure, chain validation, and hash-based verification.
"""

import copy
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BLOCKCHAIN_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "blockchain.json",
)
LEGACY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "issue_certificate.json",
)

# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------


class Block:
    """Single block in the certificate chain. Block data is stored immutably (deep copy)."""

    def __init__(
        self,
        index: int,
        timestamp: str,
        data: Any,
        previous_hash: str,
        hash_value: Optional[str] = None,
    ):
        self.index = index
        self.timestamp = timestamp
        self._data = copy.deepcopy(data) if isinstance(data, dict) else data
        self.previous_hash = previous_hash
        self.hash = hash_value if hash_value is not None else self._calculate_hash()

    @property
    def data(self) -> Any:
        return self._data

    def _calculate_hash(self) -> str:
        data_str = (
            json.dumps(self._data, sort_keys=True, separators=(",", ":"))
            if isinstance(self._data, dict)
            else str(self._data)
        )
        block_string = (
            str(self.index)
            + str(self.timestamp)
            + data_str
            + str(self.previous_hash)
        )
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": copy.deepcopy(self._data) if isinstance(self._data, dict) else self._data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Block":
        return cls(
            index=d["index"],
            timestamp=d["timestamp"],
            data=d["data"],
            previous_hash=d["previous_hash"],
            hash_value=d["hash"],
        )


class BlockchainCorruptionError(ValueError):
    """Raised when blockchain.json is corrupted or invalid."""

    pass


# ---------------------------------------------------------------------------
# Blockchain
# ---------------------------------------------------------------------------


class Blockchain:
    """
    In-memory blockchain with persistence to blockchain.json.
    Loads chain on init; saves after each add_block.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._path = storage_path or BLOCKCHAIN_FILE
        self.chain: List[Block] = self._load_or_create()
        if not self.validate_chain():
            # One-time upgrade: reindex, relink previous_hash, recompute hashes
            prev_hash = "0"
            for i, block in enumerate(self.chain):
                block.index = i
                block.previous_hash = prev_hash
                block.hash = block._calculate_hash()
                prev_hash = block.hash
            self.save()
            if not self.validate_chain():
                raise ValueError("Blockchain integrity check failed.")

    def _load_or_create(self) -> List[Block]:
        if os.path.exists(self._path):
            try:
                return self._load_chain()
            except (json.JSONDecodeError, KeyError) as e:
                raise BlockchainCorruptionError(
                    f"Blockchain file is corrupted or invalid: {self._path}. "
                    "Do not delete or overwrite; fix or replace the file."
                ) from e
        # Migrate only when blockchain.json does not exist
        if os.path.exists(LEGACY_FILE):
            try:
                chain = self._load_legacy()
                if chain:
                    self.save_chain_to_path(chain, self._path)
                    return chain
            except (json.JSONDecodeError, KeyError):
                pass
        return [self._create_genesis_block()]

    def _load_legacy(self) -> List[Block]:
        """Load chain from legacy issue_certificate.json. Runs only when blockchain.json is absent. No duplicate cert hashes."""
        with open(LEGACY_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not raw:
            return []
        blocks = []
        prev_hash = "0"
        seen_cert_hashes = set()
        for i, item in enumerate(raw):
            data = item.get("data")
            if data is None:
                data = {
                    "certificate_id": item.get("certificate_id", ""),
                    "name": item.get("name", ""),
                    "course": item.get("course", ""),
                    "date": item.get("date", ""),
                    "hash": item.get("hash", ""),
                }
            cert_hash = data.get("hash") if isinstance(data, dict) else None
            if cert_hash and cert_hash in seen_cert_hashes:
                continue
            if cert_hash:
                seen_cert_hashes.add(cert_hash)
            block = Block(
                index=len(blocks),
                timestamp=item.get("timestamp", ""),
                data=data,
                previous_hash=prev_hash,
            )
            blocks.append(block)
            prev_hash = block.hash
        return blocks

    @staticmethod
    def save_chain_to_path(chain: List[Block], path: str) -> None:
        """Write chain to JSON file (used during migration before self.chain is set)."""
        payload = {
            "chain": [b.to_dict() for b in chain],
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _create_genesis_block(self) -> Block:
        return Block(
            index=0,
            timestamp=datetime.utcnow().isoformat() + "Z",
            data="Genesis Block",
            previous_hash="0",
        )

    def _load_chain(self) -> List[Block]:
        with open(self._path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        chain_data = raw.get("chain", raw) if isinstance(raw, dict) else raw
        blocks = [Block.from_dict(b) for b in chain_data]
        if not blocks:
            return [self._create_genesis_block()]
        return blocks

    def save(self) -> None:
        """Persist chain to blockchain.json."""
        payload = {
            "chain": [b.to_dict() for b in self.chain],
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def validate_chain(self) -> bool:
        """Verify genesis block and each block's hash and previous_hash linkage."""
        if not self.chain:
            return False
        # Explicit genesis verification
        genesis = self.chain[0]
        if genesis.index != 0 or genesis.previous_hash != "0":
            return False
        if genesis.hash != genesis._calculate_hash():
            return False
        # Verify each subsequent block
        for i in range(1, len(self.chain)):
            block = self.chain[i]
            prev_block = self.chain[i - 1]
            if block.previous_hash != prev_block.hash:
                return False
            if block.hash != block._calculate_hash():
                return False
        return True

    def get_last_block(self) -> Block:
        return self.chain[-1]

    def add_block(self, data: Any) -> Block:
        last = self.get_last_block()
        new_block = Block(
            index=len(self.chain),
            timestamp=datetime.utcnow().isoformat() + "Z",
            data=data,
            previous_hash=last.hash,
        )
        self.chain.append(new_block)
        self.save()
        return new_block

    def find_block_by_cert_hash(self, cert_hash: str) -> Optional[Block]:
        """Return the first block whose data contains 'hash' == cert_hash."""
        for block in self.chain:
            if isinstance(block.data, dict) and block.data.get("hash") == cert_hash:
                return block
        return None
