"""Canonical structured certificate ledger persisted in ``blockchain.json``."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

logger = logging.getLogger(__name__)

_CHAIN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "blockchain.json")
)
_CERT_HASH = re.compile(r"[0-9a-f]{64}\Z")
_PROCESS_LOCKS: dict[str, threading.RLock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


class BlockchainCorruptionError(ValueError):
    """Raised when persisted blockchain data is malformed or fails validation."""


@contextmanager
def _exclusive_file_lock(path: str) -> Iterator[None]:
    """Lock a chain path across threads and processes while it is read-modify-written."""
    normalized_path = os.path.abspath(path)
    with _PROCESS_LOCKS_GUARD:
        process_lock = _PROCESS_LOCKS.setdefault(normalized_path, threading.RLock())

    lock_id = hashlib.sha256(os.path.normcase(normalized_path).encode()).hexdigest()
    lock_path = os.path.join(tempfile.gettempdir(), f"certauth-blockchain-{lock_id}.lock")
    with process_lock, open(lock_path, "a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            lock_file.seek(0)
            if os.fstat(lock_file.fileno()).st_size == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: str, payload: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=os.path.basename(path) + ".",
        suffix=".tmp",
        dir=directory,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


class Blockchain:
    """A validated append-only chain whose certificate identity is ``data.hash``."""

    def __init__(self, chain_path: str | os.PathLike[str] | None = None):
        self._path = os.path.abspath(os.fspath(chain_path or _CHAIN_FILE))
        self.chain: list[dict] = []
        self._payload_metadata: dict = {}
        with _exclusive_file_lock(self._path):
            if os.path.exists(self._path):
                self._load_locked()
            else:
                self.chain = [self._create_genesis_block()]
                self._save_locked()
            if not self.is_valid():
                raise BlockchainCorruptionError(
                    f"Blockchain integrity check failed: {self._path}"
                )

    @staticmethod
    def _compute_hash(index: int, timestamp: str, data, previous_hash: str) -> str:
        # Keep the existing structured block serialization. Certificate hashes
        # are separate identities stored verbatim in data["hash"].
        content = f"{index}{timestamp}{json.dumps(data, sort_keys=True)}{previous_hash}"
        return hashlib.sha256(content.encode()).hexdigest()

    @classmethod
    def _create_genesis_block(cls) -> dict:
        timestamp = _timestamp()
        data = "Genesis Block"
        return {
            "index": 0,
            "timestamp": timestamp,
            "data": data,
            "previous_hash": "0",
            "hash": cls._compute_hash(0, timestamp, data, "0"),
        }

    @classmethod
    def _new_block(cls, index: int, timestamp: str, data: dict, previous_hash: str) -> dict:
        return {
            "index": index,
            "timestamp": timestamp,
            "data": data,
            "previous_hash": previous_hash,
            "hash": cls._compute_hash(index, timestamp, data, previous_hash),
        }

    def _load_locked(self) -> None:
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise BlockchainCorruptionError(
                f"Blockchain file is unreadable: {self._path}"
            ) from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("chain"), list):
            raise BlockchainCorruptionError(
                f"Blockchain file has no valid chain: {self._path}"
            )
        self.chain = payload["chain"]
        self._payload_metadata = {
            key: value for key, value in payload.items()
            if key not in {"chain", "updated_at"}
        }
        logger.info("Blockchain loaded: %d blocks from %s", len(self.chain), self._path)

    def _save_locked(self, payload_metadata: dict | None = None) -> None:
        payload = dict(self._payload_metadata)
        payload.update(payload_metadata or {})
        payload.update({
            "chain": self.chain,
            "updated_at": _timestamp(),
        })
        _atomic_write(self._path, payload)
        self._payload_metadata = {
            key: value for key, value in payload.items()
            if key not in {"chain", "updated_at"}
        }

    @staticmethod
    def _is_iso_timestamp(value) -> bool:
        if not isinstance(value, str) or not value:
            return False
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    @classmethod
    def _is_valid_chain(cls, chain: list) -> bool:
        if not isinstance(chain, list) or not chain:
            return False

        seen_hashes: set[str] = set()
        for index, block in enumerate(chain):
            if not isinstance(block, dict):
                return False
            if type(block.get("index")) is not int or block["index"] != index:
                return False
            if not cls._is_iso_timestamp(block.get("timestamp")):
                return False
            if not isinstance(block.get("previous_hash"), str):
                return False
            stored_hash = block.get("hash")
            if not isinstance(stored_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", stored_hash):
                return False

            if index == 0:
                if (
                    block.get("data") != "Genesis Block"
                    or block["previous_hash"] != "0"
                ):
                    return False
            else:
                data = block.get("data")
                if not isinstance(data, dict):
                    return False
                cert_hash = data.get("hash")
                if not isinstance(cert_hash, str) or not _CERT_HASH.fullmatch(cert_hash):
                    return False
                if cert_hash in seen_hashes:
                    return False
                seen_hashes.add(cert_hash)
                if "legacy" in data and type(data["legacy"]) is not bool:
                    return False
                if "source" in data and not isinstance(data["source"], str):
                    return False
                if block["previous_hash"] != chain[index - 1].get("hash"):
                    return False

            try:
                calculated_hash = cls._compute_hash(
                    block["index"],
                    block["timestamp"],
                    block["data"],
                    block["previous_hash"],
                )
            except (TypeError, ValueError, OverflowError):
                return False
            if stored_hash != calculated_hash:
                return False
        return True

    def is_valid(self) -> bool:
        """Validate genesis, block structure, sequential indexes, links, and hashes."""
        return self._is_valid_chain(self.chain)

    @property
    def last_block(self) -> dict:
        if not self.chain:
            raise BlockchainCorruptionError("Blockchain has no genesis block.")
        return self.chain[-1]

    def _refresh_locked(self) -> None:
        self._load_locked()
        if not self.is_valid():
            raise BlockchainCorruptionError(
                f"Blockchain integrity check failed: {self._path}"
            )

    def add_block(self, data: dict) -> dict:
        """Append a block atomically, refusing malformed or duplicate certificate entries."""
        if not isinstance(data, dict):
            raise ValueError("Certificate block data must be an object.")
        cert_hash = data.get("hash")
        if not isinstance(cert_hash, str) or not _CERT_HASH.fullmatch(cert_hash):
            raise ValueError("Certificate block data must contain a SHA-256 hash.")

        with _exclusive_file_lock(self._path):
            self._refresh_locked()
            if self.find_by_hash(cert_hash):
                raise ValueError("Certificate hash already exists in the blockchain.")
            block = self._new_block(
                self.last_block["index"] + 1,
                _timestamp(),
                dict(data),
                self.last_block["hash"],
            )
            self.chain.append(block)
            if not self.is_valid():
                raise BlockchainCorruptionError("New block failed blockchain validation.")
            self._save_locked()
            return block

    def add_certificate_if_absent(
        self,
        cert_hash: str,
        metadata: dict | None = None,
    ) -> bool:
        """Atomically add one certificate identity; return False for duplicates."""
        if not isinstance(cert_hash, str) or not _CERT_HASH.fullmatch(cert_hash):
            raise ValueError("Certificate hash must be a SHA-256 hex digest.")
        data = dict(metadata or {})
        data["hash"] = cert_hash
        with _exclusive_file_lock(self._path):
            self._refresh_locked()
            if self.find_by_hash(cert_hash):
                return False
            block = self._new_block(
                self.last_block["index"] + 1,
                _timestamp(),
                data,
                self.last_block["hash"],
            )
            self.chain.append(block)
            if not self.is_valid():
                raise BlockchainCorruptionError("New certificate block failed validation.")
            self._save_locked()
            return True

    def find_by_hash(self, cert_hash: str) -> dict | None:
        """Return the exact certificate block matching ``data["hash"]``."""
        for block in self.chain[1:]:
            data = block.get("data", {})
            if isinstance(data, dict) and data.get("hash") == cert_hash:
                return block
        return None

    def find_all_hashes(self) -> set[str]:
        """Return certificate identities only; the genesis block is excluded."""
        return {
            block["data"]["hash"]
            for block in self.chain[1:]
            if isinstance(block.get("data"), dict)
            and isinstance(block["data"].get("hash"), str)
        }


def _load_migration_payload(path: str) -> dict:
    if not os.path.exists(path):
        return {"chain": [Blockchain._create_genesis_block()]}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise BlockchainCorruptionError(
            f"Refusing to migrate an unreadable blockchain file: {path}"
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("chain"), list):
        raise BlockchainCorruptionError(
            f"Refusing to migrate an invalid blockchain file: {path}"
        )
    return payload


def _normalize_known_legacy_genesis(chain: list) -> bool:
    """Upgrade the prior genesis-only timestamp/hash inconsistency, if recognized."""
    if len(chain) != 1:
        return False
    genesis = chain[0]
    if not isinstance(genesis, dict):
        return False
    prior_hashes = {
        Blockchain._compute_hash(0, "", "Genesis Block", "0"),
        hashlib.sha256(
            f"0{genesis.get('timestamp')}Genesis Block0".encode()
        ).hexdigest(),
    }
    if (
        genesis.get("index") != 0
        or genesis.get("data") != "Genesis Block"
        or genesis.get("previous_hash") != "0"
        or genesis.get("hash") not in prior_hashes
        or not Blockchain._is_iso_timestamp(genesis.get("timestamp"))
    ):
        return False
    genesis["hash"] = Blockchain._compute_hash(
        0, genesis["timestamp"], genesis["data"], genesis["previous_hash"]
    )
    return True


def _backup_chain(path: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base = f"{path}.pre-migration.{timestamp}.bak"
    backup = base
    suffix = 1
    while os.path.exists(backup):
        backup = f"{base}.{suffix}"
        suffix += 1
    shutil.copy2(path, backup)
    return backup


def migrate_legacy_text_ledger(chain_path: str | os.PathLike[str], legacy_path: str | os.PathLike[str]) -> dict:
    """Import the read-only text-ledger hashes without replacing existing chain data.

    The existing chain is backed up before any migration write. A migration
    marker makes subsequent calls idempotent; hashes are copied verbatim into
    ``data.hash`` and no other legacy file is consulted.
    """
    target = os.path.abspath(os.fspath(chain_path))
    source = os.path.abspath(os.fspath(legacy_path))
    with _exclusive_file_lock(target):
        payload = _load_migration_payload(target)
        migrations = payload.get("migrations", {})
        if not isinstance(migrations, dict):
            raise BlockchainCorruptionError(
                f"Blockchain migration metadata is invalid: {target}"
            )
        marker = migrations.get("blockchain.txt")
        if marker:
            chain = payload["chain"]
            if not Blockchain._is_valid_chain(chain):
                raise BlockchainCorruptionError(
                    f"Blockchain integrity check failed: {target}"
                )
            recorded = marker.get("hashes") if isinstance(marker, dict) else None
            if (
                not isinstance(recorded, list)
                or any(
                    not isinstance(cert_hash, str)
                    or not _CERT_HASH.fullmatch(cert_hash)
                    for cert_hash in recorded
                )
                or not set(recorded).issubset(
                    {block["data"]["hash"] for block in chain[1:]}
                )
            ):
                raise BlockchainCorruptionError(
                    f"Blockchain migration marker does not match its chain: {target}"
                )
            return {
                "migrated": False,
                "hashes": len(recorded),
                "added": 0,
                "backup": None,
            }
        if not os.path.exists(source):
            return {"migrated": False, "hashes": 0, "added": 0, "backup": None}

        try:
            with open(source, "r", encoding="utf-8") as handle:
                source_hashes = [
                    line.strip()
                    for line in handle
                    if line.strip()
                ]
        except OSError as exc:
            raise BlockchainCorruptionError(
                f"Unable to read legacy ledger: {source}"
            ) from exc

        if any(not _CERT_HASH.fullmatch(cert_hash) for cert_hash in source_hashes):
            raise BlockchainCorruptionError(
                f"Legacy ledger contains a value that is not a SHA-256 hash: {source}"
            )
        unique_hashes = list(dict.fromkeys(source_hashes))

        chain = payload["chain"]
        normalized_genesis = _normalize_known_legacy_genesis(chain)
        if not Blockchain._is_valid_chain(chain):
            raise BlockchainCorruptionError(
                f"Refusing to overwrite or repair invalid blockchain data: {target}"
            )
        existing_hashes = {
            block["data"]["hash"]
            for block in chain[1:]
        }
        missing = [cert_hash for cert_hash in unique_hashes if cert_hash not in existing_hashes]
        for cert_hash in missing:
            block = Blockchain._new_block(
                len(chain),
                _timestamp(),
                {
                    "hash": cert_hash,
                    "legacy": True,
                    "source": "blockchain.txt",
                },
                chain[-1]["hash"],
            )
            chain.append(block)

        if not Blockchain._is_valid_chain(chain):
            raise BlockchainCorruptionError("Migrated blockchain failed integrity validation.")

        migrations["blockchain.txt"] = {
            "source": os.path.basename(source),
            "hashes": unique_hashes,
            "migrated_at": _timestamp(),
        }
        payload["migrations"] = migrations
        payload["chain"] = chain
        payload["updated_at"] = _timestamp()

        backup = _backup_chain(target) if os.path.exists(target) else None
        _atomic_write(target, payload)
        logger.info(
            "Migrated %d legacy certificate hashes into %s (%d new blocks).",
            len(unique_hashes),
            target,
            len(missing),
        )
        return {
            "migrated": True,
            "hashes": len(unique_hashes),
            "added": len(missing),
            "backup": backup,
            "genesis_normalized": normalized_genesis,
        }
