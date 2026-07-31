"""
Simple append-only blockchain.
Each block: index, timestamp, data, previous_hash, hash.
Chain is persisted to blockchain.json.
"""
from __future__ import annotations
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_CHAIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "blockchain.json")


class Blockchain:
    def __init__(self, chain_path: str = _CHAIN_FILE):
        self._path = os.path.abspath(chain_path)
        self.chain: list[dict] = []
        self._load()

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chain = data.get("chain", [])
                logger.info("Blockchain loaded: %d blocks from %s", len(self.chain), self._path)
                return
            except Exception as e:
                logger.warning("Could not load blockchain.json (%s) — starting fresh.", e)
        self._create_genesis()

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        payload = {
            "chain": self.chain,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    # ── Genesis ───────────────────────────────────────────────────────────────

    def _create_genesis(self):
        genesis = {
            "index": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": "Genesis Block",
            "previous_hash": "0",
            "hash": self._compute_hash(0, "", "Genesis Block", "0"),
        }
        self.chain = [genesis]
        self._save()
        logger.info("Genesis block created.")

    # ── Hash ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_hash(index: int, timestamp: str, data, previous_hash: str) -> str:
        content = f"{index}{timestamp}{json.dumps(data, sort_keys=True)}{previous_hash}"
        return hashlib.sha256(content.encode()).hexdigest()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def last_block(self) -> dict:
        return self.chain[-1]

    def add_block(self, data: dict) -> dict:
        prev = self.last_block
        ts = datetime.now(timezone.utc).isoformat()
        block = {
            "index": prev["index"] + 1,
            "timestamp": ts,
            "data": data,
            "previous_hash": prev["hash"],
            "hash": self._compute_hash(prev["index"] + 1, ts, data, prev["hash"]),
        }
        self.chain.append(block)
        self._save()
        logger.info("Block #%d added (hash=%s…)", block["index"], block["hash"][:12])
        return block

    def find_by_hash(self, cert_hash: str) -> dict | None:
        """Return the block whose data contains this cert hash, or None."""
        for block in self.chain[1:]:  # skip genesis
            data = block.get("data", {})
            if isinstance(data, dict) and data.get("hash") == cert_hash:
                return block
        return None

    def find_all_hashes(self) -> set[str]:
        """Return all certificate hashes stored on chain."""
        hashes = set()
        for block in self.chain[1:]:
            data = block.get("data", {})
            if isinstance(data, dict) and "hash" in data:
                hashes.add(data["hash"])
        return hashes

    def is_valid(self) -> bool:
        """Validate chain linkage (previous_hash pointers only)."""
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.get("previous_hash") != prev.get("hash"):
                return False
        return True
