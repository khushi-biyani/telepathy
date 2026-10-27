"""Cached Tavily search for the research topology. One basic search = 1 credit (free tier: 1,000 a
month). Responses are cached by query for 7 days so demos are reproducible and credits are saved.
The key comes from TAVILY_API_KEY in .env and is never printed."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import httpx

from ..llm import REPO_DIR  # also loads .env
from ..trust import Content, untrusted

CACHE_DIR = REPO_DIR / ".cache" / "tavily"
TTL_SECONDS = 7 * 24 * 3600
URL = "https://api.tavily.com/search"


class TavilyError(RuntimeError):
    pass


def _post(query: str, max_results: int) -> dict:
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise TavilyError("TAVILY_API_KEY is not set. Put it in .env (never in code).")
    r = httpx.post(URL, headers={"Authorization": f"Bearer {key}"}, timeout=30,
                   json={"query": query, "max_results": max_results, "search_depth": "basic"})
    if r.status_code != 200:
        raise TavilyError(f"Tavily returned HTTP {r.status_code}")
    return r.json()


def search(query: str, max_results: int = 5, cache_dir: Path | None = None) -> list[dict]:
    """[{title, url, content}] for the query. Served from cache when fresh."""
    cache_dir = cache_dir or CACHE_DIR
    f = cache_dir / (hashlib.sha256(f"{query}|{max_results}".encode()).hexdigest() + ".json")
    if f.exists() and time.time() - f.stat().st_mtime < TTL_SECONDS:
        return json.loads(f.read_text())
    results = [{"title": x.get("title", ""), "url": x.get("url", ""), "content": x.get("content", "")}
               for x in _post(query, max_results).get("results", [])]
    cache_dir.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(results))
    return results


def as_content(results: list[dict], max_chars: int = 500) -> list[Content]:
    """Search results as UNTRUSTED Content, labelled here at the point of entry (Section 8a.1).
    Nothing downstream, and no model output, can change these labels."""
    return [untrusted(f"{r['title']}: {r['content'][:max_chars]}", f"tavily:{r['url']}") for r in results]


def format_results(results: list[dict], max_chars: int = 500) -> str:
    """Numbered text block for the Researcher's prompt, so the Writer can cite [1], [2]..."""
    return "\n".join(f"[{i}] {r['title']} ({r['url']}): {r['content'][:max_chars]}"
                     for i, r in enumerate(results, 1))
