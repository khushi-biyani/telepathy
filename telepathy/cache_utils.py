"""Helpers for the shared working memory (KV cache)."""
from __future__ import annotations

import copy


def fork(cache):
    """A deep copy for side branches (subtitles, honesty check). Never mutates `cache`.
    Verified on transformers 5.x DynamicCache (tests/test_cache.py)."""
    return None if cache is None else copy.deepcopy(cache)


def length(cache) -> int:
    """Current sequence length held in the cache (0 for no cache)."""
    return 0 if cache is None else int(cache.get_seq_length())


class CacheOwnershipError(RuntimeError):
    pass


def keep_last(cache, n: int):
    """Keep only the last `n` positions of the cache (in place). n <= 0 gives no cache at all.
    Used for `thoughts_only` sharing: hand over the sender's silent steps, not its input history."""
    if cache is None or n <= 0:
        return None
    if length(cache) <= n:
        return cache
    for layer in cache.layers:
        layer.keys = layer.keys[:, :, -n:, :].contiguous()
        layer.values = layer.values[:, :, -n:, :].contiguous()
    return cache


def bind(cache, run_id: str):
    """Tie a cache to the run that made it (Section 8a.6: one trust zone). Survives fork()."""
    if cache is not None:
        cache._telepathy_run_id = run_id
    return cache


def assert_bound(cache, run_id: str) -> None:
    if cache is not None and getattr(cache, "_telepathy_run_id", None) != run_id:
        raise CacheOwnershipError("a working-memory cache can only be used by the run that created it")
