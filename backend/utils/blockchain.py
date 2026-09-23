"""Canonical structured certificate ledger."""
from __future__ import annotations
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_CHAIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "blockchain.json")
_LEGACY_TEXT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "blockchain.txt")


class Blockchain:
    def __init__(self, chain_path: str = _CHAIN_FILE, legacy_path: str | None = None):
        self._path = os.path.abspath(chain_path)
        explicit_legacy_path = legacy_path is not None
        self._legacy_path = (
            os.path.abspath(legacy_path) if legacy_path is not None
            else os.path.abspath(_LEGACY_TEXT_FILE)
        )
        self._migrate_explicit_legacy = explicit_legacy_path
        self.chain: list[dict] = []
        self._load()
        self._migrate_legacy_hashes()

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chain = data.get("chain", [])
                logger.info("Blockchain loaded: %d blocks from %s", len(self.chain), self._path)
                return
            except (OSError, json.JSONDecodeError, TypeError, AttributeError) as e:
                logger.warning("Could not load blockchain.json (%s) — starting fresh.", e)
        self._create_genesis()

    def _migrate_legacy_hashes(self):
        """Copy legacy hash-only entries without deleting or rewriting the source."""
        if (
            (self._path != os.path.abspath(_CHAIN_FILE) and not self._migrate_explicit_legacy)
            or not os.path.exists(self._legacy_path)
        ):
            return
        try:
            with open(self._legacy_path, "r", encoding="utf-8") as f:
                legacy_hashes = {line.strip() for line in f if line.strip()}
        except OSError as e:
            logger.warning("Could not read legacy blockchain.txt (%s)", e)
            return

        existing = self.find_all_hashes()
        migrated = sorted(legacy_hashes - existing)
        for cert_hash in migrated:
            self.add_block({"hash": cert_hash, "migrated_from": "blockchain.txt"})
        if migrated:
            logger.info("Migrated %d legacy certificate hashes into blockchain.json", len(migrated))

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
        timestamp = datetime.now(timezone.utc).isoformat()
        genesis = {
            "index": 0,
            "timestamp": timestamp,
            "data": "Genesis Block",
            "previous_hash": "0",
            "hash": self._compute_hash(0, timestamp, "Genesis Block", "0"),
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
        """Validate block hashes and previous-hash linkage."""
        if not self.chain:
            return False
        genesis = self.chain[0]
        expected_genesis_hash = self._compute_hash(
            genesis.get("index"),
            genesis.get("timestamp"),
            genesis.get("data"),
            genesis.get("previous_hash"),
        )
        legacy_genesis_hash = self._compute_hash(
            genesis.get("index"), "", genesis.get("data"), genesis.get("previous_hash")
        )
        if (
            genesis.get("index") != 0
            or genesis.get("previous_hash") != "0"
            or genesis.get("hash") not in {expected_genesis_hash, legacy_genesis_hash}
        ):
            return False
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if (
                curr.get("index") != i
                or curr.get("previous_hash") != prev.get("hash")
                or curr.get("hash") != self._compute_hash(
                    curr.get("index"),
                    curr.get("timestamp"),
                    curr.get("data"),
                    curr.get("previous_hash"),
                )
            ):
                return False
        return True

    def validate_chain(self) -> bool:
        """Compatibility alias for callers of the former implementation."""
        return self.is_valid()

    def find_block_by_cert_hash(self, cert_hash: str) -> dict | None:
        """Compatibility alias for the canonical hash lookup."""
        return self.find_by_hash(cert_hash)
