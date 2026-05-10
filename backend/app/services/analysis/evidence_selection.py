from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.services.analysis.search_query import clean_search_term

_SPLIT_RE = re.compile(r"[，。！？；、,:;!?\n\r\t]+")
_CONNECTOR_RE = re.compile(r"\b(?:and|or|with|for)\b|和|与|及|以及|并且|还有")
_EN_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+\-_/]{2,}")
_CJK_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,16}")
_SPACE_RE = re.compile(r"\s+")

_GENERIC_PREFIXES = (
    "我想研究",
    "想研究",
    "我想看清",
    "想看清",
    "帮跨境电商卖家看清",
    "帮用户看清",
    "帮用户解决",
    "帮团队解决",
    "帮大家解决",
    "帮",
    "判断有没有",
    "看看有没有",
    "想看看有没有",
    "面向",
    "针对",
)

_GENERIC_SUFFIXES = (
    "的真实痛点",
    "真实痛点",
    "的痛点",
    "痛点",
    "的问题",
    "问题",
    "工具机会",
    "产品机会",
    "机会",
    "工具",
    "助手",
    "方案",
    "赛道",
)

_EN_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "need",
    "want",
    "looking",
    "help",
    "user",
    "users",
    "tool",
    "tools",
    "problem",
    "problems",
    "issue",
    "issues",
}


@dataclass(frozen=True, slots=True)
class EvidenceSelectionInput:
    product_description: str
    keywords: Sequence[str] = ()
    route_reasons: Sequence[str] = ()
    preferred_communities: Sequence[str] = ()
    min_score: float = 1.5
    min_matched_terms: int = 1


@dataclass(frozen=True, slots=True)
class EvidenceSelectionDiagnostics:
    phrases: tuple[str, ...]
    tokens: tuple[str, ...]
    matched_posts: int
    fallback_used: bool


@dataclass(frozen=True, slots=True)
class EvidenceSelectionResult:
    posts: list[dict[str, Any]]
    diagnostics: EvidenceSelectionDiagnostics


@dataclass(frozen=True, slots=True)
class _WeightedTerm:
    text: str
    weight: float


def _is_specific_phrase(value: str) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return bool(" " in text or _CJK_TOKEN_RE.search(text))


def _strip_generic_phrase(fragment: str) -> str:
    text = str(fragment or "").strip().lower()
    if not text:
        return ""
    for prefix in _GENERIC_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    for suffix in _GENERIC_SUFFIXES:
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    text = text.strip("()[]{}<>\"'“”‘’`~·-_/\\|")
    return _SPACE_RE.sub(" ", text).strip()


def _extract_focus_phrases(text: str) -> list[str]:
    if not str(text or "").strip():
        return []
    phrases: list[str] = []
    seen: set[str] = set()
    for fragment in _SPLIT_RE.split(str(text)):
        for part in _CONNECTOR_RE.split(fragment):
            normalized = _strip_generic_phrase(part)
            if not normalized or len(normalized) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            phrases.append(normalized)
    return phrases


def _extract_tokens(text: str) -> set[str]:
    raw = str(text or "").lower()
    english = {
        token
        for token in _EN_TOKEN_RE.findall(raw)
        if token not in _EN_STOPWORDS
    }
    cjk = {token for token in _CJK_TOKEN_RE.findall(str(text or "")) if token}
    return {token for token in english | cjk if token}


def _build_weighted_terms(
    *,
    product_description: str,
    keywords: Sequence[str],
    route_reasons: Sequence[str],
) -> tuple[list[_WeightedTerm], dict[str, float]]:
    phrases: list[_WeightedTerm] = []
    tokens: dict[str, float] = {}
    seen_phrases: set[str] = set()

    def _push_phrase(raw: str, weight: float) -> None:
        normalized = _strip_generic_phrase(raw)
        if not normalized or len(normalized) < 2:
            return
        if normalized not in seen_phrases:
            seen_phrases.add(normalized)
            phrases.append(_WeightedTerm(normalized, weight))
        for token in _extract_tokens(normalized):
            tokens[token] = max(tokens.get(token, 0.0), round(weight * 0.65, 3))

    for phrase in _extract_focus_phrases(product_description):
        _push_phrase(phrase, 1.0)
    for keyword in keywords:
        cleaned = clean_search_term(str(keyword or ""))
        if cleaned:
            _push_phrase(cleaned, 1.8 if " " in cleaned else 1.4)
        else:
            _push_phrase(str(keyword or ""), 1.4)
    for reason in route_reasons:
        _push_phrase(reason, 1.1)

    return phrases, tokens


def _normalize_post_text(post: Mapping[str, Any]) -> tuple[str, str, set[str], str]:
    raw_title = str(post.get("title") or "").strip()
    raw_text = " ".join(
        [
            raw_title,
            str(post.get("summary") or ""),
            str(post.get("body") or ""),
            str(post.get("selftext") or ""),
        ]
    ).strip()
    normalized_title = _SPACE_RE.sub(" ", raw_title.lower()).strip()
    normalized_text = _SPACE_RE.sub(" ", raw_text.lower()).strip()
    raw_subreddit = str(post.get("subreddit") or post.get("community") or "").strip()
    subreddit = raw_subreddit.lower()
    return normalized_title, normalized_text, _extract_tokens(raw_text), subreddit


def select_evidence_posts(
    posts: Sequence[Mapping[str, Any]],
    selection_input: EvidenceSelectionInput,
) -> EvidenceSelectionResult:
    raw_posts = [dict(post) for post in posts if isinstance(post, Mapping)]
    if not raw_posts:
        return EvidenceSelectionResult(
            posts=[],
            diagnostics=EvidenceSelectionDiagnostics(
                phrases=(),
                tokens=(),
                matched_posts=0,
                fallback_used=False,
            ),
        )

    phrases, token_weights = _build_weighted_terms(
        product_description=selection_input.product_description,
        keywords=selection_input.keywords,
        route_reasons=selection_input.route_reasons,
    )
    if not phrases and not token_weights:
        return EvidenceSelectionResult(
            posts=raw_posts,
            diagnostics=EvidenceSelectionDiagnostics(
                phrases=(),
                tokens=(),
                matched_posts=len(raw_posts),
                fallback_used=True,
            ),
        )

    preferred = {
        str(name or "").strip().lower()
        for name in selection_input.preferred_communities
        if str(name or "").strip()
    }
    scored: list[tuple[int, float, int, int, dict[str, Any]]] = []

    for index, post in enumerate(raw_posts):
        normalized_title, normalized_text, post_tokens, subreddit = _normalize_post_text(post)
        score = 0.0
        matched_terms: set[str] = set()
        phrase_hits = 0
        token_hits = 0

        for phrase in phrases:
            if phrase.text and phrase.text in normalized_title:
                score += phrase.weight * 2.2
                matched_terms.add(phrase.text)
                if _is_specific_phrase(phrase.text):
                    phrase_hits += 1
            elif phrase.text and phrase.text in normalized_text:
                score += phrase.weight * 1.8
                matched_terms.add(phrase.text)
                if _is_specific_phrase(phrase.text):
                    phrase_hits += 1
        for token, weight in token_weights.items():
            if token in post_tokens:
                score += weight
                matched_terms.add(token)
                token_hits += 1

        preferred_hit = bool(preferred and subreddit in preferred)
        if preferred_hit:
            score += 0.75

        if (
            score >= selection_input.min_score
            and len(matched_terms) >= selection_input.min_matched_terms
            and (phrase_hits >= 1 or token_hits >= 2 or (preferred_hit and token_hits >= 1))
        ):
            scored.append((phrase_hits, score, len(matched_terms), -index, dict(post)))

    if not scored:
        return EvidenceSelectionResult(
            posts=raw_posts,
            diagnostics=EvidenceSelectionDiagnostics(
                phrases=tuple(term.text for term in phrases[:12]),
                tokens=tuple(sorted(token_weights.keys())[:20]),
                matched_posts=0,
                fallback_used=True,
            ),
        )

    scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
    filtered = [post for _, _, _, _, post in scored]
    return EvidenceSelectionResult(
        posts=filtered,
        diagnostics=EvidenceSelectionDiagnostics(
            phrases=tuple(term.text for term in phrases[:12]),
            tokens=tuple(sorted(token_weights.keys())[:20]),
            matched_posts=len(filtered),
            fallback_used=False,
        ),
    )


__all__ = [
    "EvidenceSelectionDiagnostics",
    "EvidenceSelectionInput",
    "EvidenceSelectionResult",
    "select_evidence_posts",
]
