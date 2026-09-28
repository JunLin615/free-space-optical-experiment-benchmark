"""Dependency-free deterministic retrieval from the optional example library."""

from __future__ import annotations

import hashlib
import math
import re
import time
from collections import Counter

from tools.case_library import INDEX_PATH, load_index, load_items
from tools.protocols import load_protocol


RETRIEVAL_VERSION = "lexical_v1.0.0"
WORD_RE = re.compile(r"[a-z]+(?:[-_][a-z]+)*|\d+(?:\.\d+)?", re.I)
STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
        "in", "is", "it", "of", "on", "or", "the", "this", "to", "with", "which"}


def _terms(text: str) -> list[str]:
    return [term for term in WORD_RE.findall(text.lower()) if term not in STOP]


def _estimated_tokens(text: str) -> int:
    # Transparent local approximation, never represented as provider token usage.
    return len(WORD_RE.findall(text))


def retrieve(query: str, max_items: int = 3,
             protocol_id: str = "case_assisted") -> dict:
    protocol = load_protocol(protocol_id)
    policy = protocol["retrieval_policy"]
    if not protocol["case_library_access"]["enabled"]:
        raise ValueError(f"protocol {protocol_id} forbids case-library retrieval")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("retrieval query must be nonempty")
    if not isinstance(max_items, int) or not 0 <= max_items <= policy["max_items"]:
        raise ValueError("max_items exceeds protocol cap")
    started = time.perf_counter()
    items = load_items()
    terms = set(_terms(query))
    document_terms = [Counter(_terms(item["text"])) for item in items]
    df = Counter(term for counts in document_terms for term in counts)
    scored = []
    for item, counts in zip(items, document_terms):
        score = sum((1.0 + math.log(counts[term])) *
                    math.log((len(items) + 1) / (df[term] + 0.5))
                    for term in terms if counts[term])
        scored.append((round(score, 8), item))
    scored.sort(key=lambda row: (-row[0], row[1]["item_id"]))
    selected = []
    total_tokens = 0
    for score, item in scored:
        if len(selected) >= max_items or score <= 0:
            break
        tokens = _estimated_tokens(item["text"])
        if total_tokens + tokens > policy["max_context_tokens"]:
            continue
        selected.append({"item_id": item["item_id"], "text": item["text"],
                         "content_sha256": item["content_sha256"],
                         "estimated_tokens": tokens, "score": score})
        total_tokens += tokens
    return {
        "query": query,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "retrieval_version": RETRIEVAL_VERSION,
        "library_snapshot_id": load_index()["snapshot_id"],
        "library_index_sha256": hashlib.sha256(INDEX_PATH.read_bytes()).hexdigest(),
        "retrieved_ids": [item["item_id"] for item in selected],
        "scores": [item["score"] for item in selected],
        "items": selected,
        "item_count": len(selected),
        "total_retrieved_tokens": total_tokens,
        "latency_seconds": time.perf_counter() - started,
    }
