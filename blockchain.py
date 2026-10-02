"""Compatibility import for the canonical blockchain implementation.

New code should import :class:`backend.utils.blockchain.Blockchain` directly.
This module intentionally contains no separate storage or validation logic.
"""

from backend.utils.blockchain import Blockchain

__all__ = ["Blockchain"]
