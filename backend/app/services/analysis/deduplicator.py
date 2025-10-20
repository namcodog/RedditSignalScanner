from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List, Sequence, Set

import yaml
from datasketch import MinHash, MinHashLSH

STOPWORDS = {
    "the",
    "a",
    "an",
    "to",
    "for",
    "and",
    "with",
    "that",
    "this",
    "those",
    "these",
    "in",
    "on",
    "of",
    "weekly",
    "reports",
    "report",
    "summaries",
    "summary",
    "ai",
}

_DEFAULT_MINHASH_THRESHOLD = 0.85
_DEDUP_CONFIG_PATH = Path("config/deduplication.yaml")
_CONFIG_CACHE: Dict[str, Any] = {"threshold": _DEFAULT_MINHASH_THRESHOLD, "mtime": None}
_CONFIG_LOCK = Lock()


def _load_minhash_threshold(config_path: Path = _DEDUP_CONFIG_PATH) -> float:
    try:
        mtime = config_path.stat().st_mtime
    except FileNotFoundError:
        return _DEFAULT_MINHASH_THRESHOLD

    with _CONFIG_LOCK:
        cached_mtime = _CONFIG_CACHE.get("mtime")
        if cached_mtime == mtime:
            return float(_CONFIG_CACHE["threshold"])

        with config_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}

        value = payload.get("minhash_threshold", _DEFAULT_MINHASH_THRESHOLD)
        try:
            threshold = float(value)
        except (TypeError, ValueError):
            threshold = _DEFAULT_MINHASH_THRESHOLD

        _CONFIG_CACHE["threshold"] = threshold
        _CONFIG_CACHE["mtime"] = mtime
        return threshold


def _tokenise(text: str) -> List[str]:
    text_lower = text.lower()
    word_tokens = [
        token for token in re.findall(r"[a-z0-9]{2,}", text_lower) if len(token) >= 2
    ]
    bigrams = [
        f"{word_tokens[i]}_{word_tokens[i + 1]}" for i in range(len(word_tokens) - 1)
    ]
    normalised = re.sub(r"\s+", " ", text_lower)
    shingle_length = 5
    if len(normalised) < shingle_length:
        char_shingles: set[str] = set()
    else:
        char_shingles = {
            normalised[idx : idx + shingle_length]
            for idx in range(len(normalised) - shingle_length + 1)
        }
    return word_tokens + bigrams + list(char_shingles)


def _normalise_for_sequence(text: str) -> str:
    tokens = [
        token for token in re.findall(r"[a-z]+", text.lower()) if token not in STOPWORDS
    ]
    return " ".join(tokens)


def _build_minhash(tokens: Iterable[str], num_perm: int) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for token in tokens:
        m.update(token.encode("utf-8"))
    return m


def _jaccard_similarity(tokens_a: Iterable[str], tokens_b: Iterable[str]) -> float:
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return intersection / union


def _cluster_posts(
    token_sets: Sequence[List[str]],
    texts: Sequence[str],
    *,
    threshold: float,
    num_perm: int,
) -> List[List[int]]:
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    minhashes: List[MinHash] = []
    for idx, tokens in enumerate(token_sets):
        mh = _build_minhash(tokens, num_perm)
        lsh.insert(str(idx), mh)
        minhashes.append(mh)

    adjacency: Dict[int, Set[int]] = {i: set() for i in range(len(token_sets))}
    for idx, mh in enumerate(minhashes):
        candidate_keys = lsh.query(mh)
        candidate_indices = {int(key) for key in candidate_keys if int(key) != idx}
        if not candidate_indices:
            candidate_indices = set(range(len(token_sets)))
            candidate_indices.discard(idx)
        for cand_idx in candidate_indices:
            jaccard = _jaccard_similarity(token_sets[idx], token_sets[cand_idx])
            sequence_ratio = SequenceMatcher(
                None,
                texts[idx],
                texts[cand_idx],
            ).ratio()
            similarity = max(jaccard, sequence_ratio)
            if similarity >= threshold:
                adjacency[idx].add(cand_idx)
                adjacency[cand_idx].add(idx)

    clusters: List[List[int]] = []
    visited: Set[int] = set()
    for idx in range(len(token_sets)):
        if idx in visited:
            continue
        queue = [idx]
        cluster: List[int] = []
        visited.add(idx)
        while queue:
            current = queue.pop()
            cluster.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        clusters.append(sorted(cluster))
    return clusters


def deduplicate_posts(
    posts: Sequence[Dict[str, object]],
    *,
    threshold: float | None = None,
    num_perm: int = 128,
) -> List[Dict[str, object]]:
    """
    Collapse near-duplicate posts using MinHash + LSH.

    Returns a list of posts enriched with duplicate metadata:
        - duplicate_ids: list of aggregated duplicate post identifiers
        - evidence_count: number of posts supporting the insight
        - evidence_post_ids: all ids contributing to the cluster (primary + duplicates)
    """
    if not posts:
        return []

    token_sets: List[List[str]] = []
    normalised_texts: List[str] = []
    for idx, post in enumerate(posts):
        text = f"{post.get('title', '')} {post.get('summary', '')}"
        tokens = _tokenise(text)
        if not tokens:
            tokens = [str(post.get("id", idx))]
        token_sets.append(tokens)
        normalised_texts.append(_normalise_for_sequence(text))

    effective_threshold = threshold if threshold is not None else _load_minhash_threshold()

    clusters = _cluster_posts(
        token_sets,
        normalised_texts,
        threshold=effective_threshold,
        num_perm=num_perm,
    )
    enriched: List[Dict[str, object]] = []

    for cluster in clusters:
        if not cluster:
            continue

        def engagement(index: int) -> float:
            post = posts[index]
            score_val: Any = post.get("score", 0) or 0
            comments_val: Any = post.get("num_comments", 0) or 0
            score = float(score_val)
            comments = float(comments_val)
            return score + comments * 0.75

        primary_index = max(cluster, key=engagement)
        duplicates = [idx for idx in cluster if idx != primary_index]

        primary = dict(posts[primary_index])
        duplicate_ids = [str(posts[idx].get("id", idx)) for idx in duplicates]
        evidence_ids = [str(primary.get("id", primary_index))] + duplicate_ids

        primary["duplicate_ids"] = duplicate_ids
        primary["evidence_count"] = len(cluster)
        primary["evidence_post_ids"] = evidence_ids

        enriched.append(primary)

    return enriched


__all__ = ["deduplicate_posts"]
