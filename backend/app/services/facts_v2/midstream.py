from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import re
from typing import cast

from app.services.topic_profiles import TopicProfile


def compute_source_range(
    *, posts: Sequence[Mapping[str, object]], comments: Sequence[Mapping[str, object]]
) -> dict[str, int]:
    """source_range 的口径：本次事实包实际参与分析的样本量（不是 days）。"""
    return {"posts": len(posts), "comments": len(comments)}


# Phase2/3 将逐步补齐：先让调用方与单测有稳定入口。


def compute_pain_clusters_v2(
    *,
    posts: Sequence[Mapping[str, object]],
    comments: Sequence[Mapping[str, object]],
    profile: TopicProfile,
    domain_pain_config: Mapping[str, object] | None = None,
    max_clusters: int = 5,
    min_mentions: int = 10,
    min_unique_authors: int = 5,
    max_evidence: int = 5,
) -> list[dict[str, object]]:
    """
    生成 pain_clusters v2（有数字、有证据）。

    口径（人话版）：
    - “mentions”= 这类抱怨被提到多少次（按条数算）
    - “unique_authors”= 多少个不同的人在吐槽/讨论它
    - “evidence_quote_ids”= 我们能拿得出手的原话证据（comment quote_id）
    """
    config = _resolve_domain_pain_config(domain_pain_config)
    domains = _pick_domains_for_profile(profile, config)
    phrase_map = _collect_domain_phrases(config, domains)
    if not phrase_map:
        return []

    counts: dict[str, int] = defaultdict(int)
    authors: dict[str, set[str]] = defaultdict(set)
    evidence: dict[str, list[tuple[int, str]]] = defaultdict(list)  # score, quote_id

    def _handle_item(item: Mapping[str, object], *, is_comment: bool) -> None:
        text = _extract_text(item)
        if not text:
            return
        normalized = _normalize_text(text)
        if _hits_any(normalized.cleaned_lower, profile.exclude_keywords_any):
            return
        author_id = _get_str(item, "author_id") or None
        quote_id = _get_str(item, "quote_id") or _get_str(item, "comment_id")
        comment_score = _get_int(item, "comment_score")
        for phrase_key, phrase_tokens in phrase_map.items():
            if not _match_phrase_tokens(normalized.cleaned_lower, phrase_tokens):
                continue
            counts[phrase_key] += 1
            if author_id:
                authors[phrase_key].add(author_id)
            if is_comment and quote_id:
                evidence[phrase_key].append((comment_score, quote_id))

    for post in posts:
        _handle_item(post, is_comment=False)
    for comment in comments:
        _handle_item(comment, is_comment=True)

    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    out: list[dict[str, object]] = []
    for idx, (phrase_key, mentions) in enumerate(ranked[:max_clusters], start=1):
        uniq = len(authors.get(phrase_key, set()))
        if mentions < min_mentions or uniq < min_unique_authors:
            continue
        ev_sorted = sorted(evidence.get(phrase_key, []), key=lambda x: x[0], reverse=True)
        ev_ids = [qid for _, qid in ev_sorted][:max_evidence]
        if not ev_ids:
            continue
        out.append(
            {
                "cluster_id": f"p_{idx:03d}",
                "tag": phrase_key,
                "title": _phrase_key_to_title(phrase_key),
                "metrics": {"mentions": mentions, "unique_authors": uniq},
                "top_entities": {"brand": []},
                "evidence_quote_ids": ev_ids,
                "confidence": None,
            }
        )
    return out


def compute_brand_pain_v2(
    *,
    posts: Sequence[Mapping[str, object]],
    comments: Sequence[Mapping[str, object]],
    profile: TopicProfile,
    pain_clusters: Sequence[Mapping[str, object]],
    brand_candidates: Sequence[str] | None = None,
    min_mentions: int = 3,
    min_unique_authors: int = 2,
    min_evidence: int = 3,
    max_items: int = 10,
    max_evidence: int = 5,
) -> list[dict[str, object]]:
    """
    生成 brand_pain v2：让“mentions>0 但 unique_authors=0”这种假数据直接消失。

    注意：这是“品牌 × 痛点”维度；如果缺痛点（pain_clusters 为空），这里会返回空。
    """
    clusters = list(pain_clusters or [])
    if not clusters:
        return []
    tag_to_cluster_id = {
        _get_str(c, "tag"): _get_str(c, "cluster_id")
        for c in clusters
        if _get_str(c, "tag") and _get_str(c, "cluster_id")
    }
    if not tag_to_cluster_id:
        return []

    candidates = _normalize_brand_candidates(brand_candidates, profile)
    if not candidates:
        return []

    mentions: dict[tuple[str, str], int] = defaultdict(int)  # (brand, cluster_id) -> cnt
    authors: dict[tuple[str, str], set[str]] = defaultdict(set)
    evidence: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)  # score, quote_id

    # Pre-tokenize phrase tags for matching
    tag_tokens: dict[str, tuple[str, ...]] = {
        tag: tuple(tag.split())
        for tag in tag_to_cluster_id
        if tag and isinstance(tag, str)
    }

    def _handle_item(item: Mapping[str, object], *, is_comment: bool) -> None:
        text = _extract_text(item)
        if not text:
            return
        normalized = _normalize_text(text)
        if _hits_any(normalized.cleaned_lower, profile.exclude_keywords_any):
            return
        author_id = _get_str(item, "author_id") or None
        quote_id = _get_str(item, "quote_id") or _get_str(item, "comment_id")
        comment_score = _get_int(item, "comment_score")

        matched_brands = _match_brands(normalized.cleaned_lower, candidates)
        if not matched_brands:
            return

        matched_cluster_ids: list[str] = []
        for tag, cid in tag_to_cluster_id.items():
            tokens = tag_tokens.get(tag, ())
            if tokens and _match_phrase_tokens(normalized.cleaned_lower, tokens):
                matched_cluster_ids.append(cid)
        if not matched_cluster_ids:
            return

        for brand in matched_brands:
            for cid in matched_cluster_ids:
                key = (brand, cid)
                mentions[key] += 1
                if author_id:
                    authors[key].add(author_id)
                if is_comment and quote_id:
                    evidence[key].append((comment_score, quote_id))

    for post in posts:
        _handle_item(post, is_comment=False)
    for comment in comments:
        _handle_item(comment, is_comment=True)

    ranked = sorted(mentions.items(), key=lambda kv: kv[1], reverse=True)
    out: list[dict[str, object]] = []
    for (brand, cid), cnt in ranked:
        uniq = len(authors.get((brand, cid), set()))
        ev_sorted = sorted(evidence.get((brand, cid), []), key=lambda x: x[0], reverse=True)
        ev_ids = [qid for _, qid in ev_sorted][:max_evidence]
        status = "ok"
        reason = ""
        if cnt < min_mentions:
            status = "insufficient_sample"
            reason = f"mentions<{min_mentions}"
        elif uniq < min_unique_authors:
            status = "insufficient_sample"
            reason = f"unique_authors<{min_unique_authors}"
        elif len(ev_ids) < min_evidence:
            status = "insufficient_sample"
            reason = f"evidence<{min_evidence}"

        out.append(
            {
                "brand": brand,
                "pain_cluster_id": cid,
                "mentions": cnt,
                "unique_authors": uniq,
                "evidence_quote_ids": ev_ids,
                "filters_applied": ["topic_profile", "pain_cluster_match"],
                "status": status,
                "reason": reason or None,
            }
        )
        if len(out) >= max_items:
            break
    return out


def filter_solutions_by_profile(
    solutions: Sequence[Mapping[str, object]],
    *,
    profile: TopicProfile,
    max_items: int = 10,
) -> list[dict[str, object]]:
    """
    宁缺毋滥：solutions 只保留“明显在聊这个赛道”的建议句子。
    - 命中 required_entities_any 或 soft_required_entities_any 才算入场券
    - 命中 exclude_keywords_any 直接丢弃
    """
    required = tuple(_normalize_terms(profile.required_entities_any))
    soft = tuple(_normalize_terms(profile.soft_required_entities_any))
    includes = tuple(_normalize_terms(profile.include_keywords_any))
    excludes = tuple(_normalize_terms(profile.exclude_keywords_any))

    kept: list[tuple[int, dict[str, object]]] = []
    for sol in solutions:
        desc = _get_str(sol, "description")
        if not desc:
            continue
        normalized = _normalize_text(desc)
        if _hits_any(normalized.cleaned_lower, excludes):
            continue
        required_hit = _hits_any(normalized.cleaned_lower, required)
        soft_hit = _hits_any(normalized.cleaned_lower, soft)
        if not (required_hit or soft_hit):
            continue
        include_hits = _count_hits(normalized.cleaned_lower, includes)
        score = (2 if required_hit else 1) + include_hits
        kept.append((score, {"description": desc, **{k: v for k, v in sol.items() if k != "description"}}))

    kept.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in kept][:max_items]


_LINK_MD_RE = re.compile(r"\s*\[🔗\]\([^)]*\)")


@dataclass(frozen=True, slots=True)
class _NormalizedText:
    raw: str
    cleaned_lower: str


def _normalize_text(text: str) -> _NormalizedText:
    raw = text or ""
    cleaned = _LINK_MD_RE.sub("", raw).strip().lower()
    return _NormalizedText(raw=raw, cleaned_lower=cleaned)


def _get_str(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _get_int(row: Mapping[str, object], key: str) -> int:
    value = row.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _extract_text(item: Mapping[str, object]) -> str:
    for key in ("text", "body", "title"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _normalize_terms(terms: Iterable[str]) -> list[str]:
    return [t.strip().lower() for t in terms if isinstance(t, str) and t.strip()]


def _hits_any(text_lower: str, terms: Iterable[str]) -> bool:
    return any(t in text_lower for t in terms if t)


def _count_hits(text_lower: str, terms: Iterable[str]) -> int:
    return sum(1 for t in terms if t and t in text_lower)


def _match_phrase_tokens(text_lower: str, phrase_tokens: Sequence[str]) -> bool:
    return all(tok and tok in text_lower for tok in phrase_tokens)


def _slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return s or "unknown"


def _resolve_domain_pain_config(domain_pain_config: Mapping[str, object] | None) -> Mapping[str, object]:
    if domain_pain_config is not None:
        return domain_pain_config
    default_path = Path(__file__).resolve().parents[3] / "config" / "domain_pain_points.yml"
    if not default_path.exists():
        return {}
    try:
        import yaml  # local import: avoid global YAML dependency in unit tests

        payload = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, Mapping):
            return {}
        domains = payload.get("domains")
        if isinstance(domains, Mapping):
            return cast(Mapping[str, object], domains)
        return {}
    except Exception:
        return {}


def _pick_domains_for_profile(profile: TopicProfile, config: Mapping[str, object]) -> list[str]:
    allowed = {c.lower() for c in profile.allowed_communities if c}
    picked: list[str] = []
    for domain, spec in config.items():
        if not isinstance(spec, Mapping):
            continue
        subs = spec.get("subreddits")
        if not isinstance(subs, Iterable):
            continue
        norm_subs = {str(s).lower() for s in subs if s}
        if allowed and norm_subs.intersection(allowed):
            picked.append(str(domain))
    return picked


def _collect_domain_phrases(config: Mapping[str, object], domains: Sequence[str]) -> dict[str, tuple[str, ...]]:
    phrases: dict[str, tuple[str, ...]] = {}
    for domain in domains:
        spec = config.get(domain)
        if not isinstance(spec, Mapping):
            continue
        pain_keywords = spec.get("pain_keywords")
        if not isinstance(pain_keywords, Mapping):
            continue
        for _, items in pain_keywords.items():
            if not isinstance(items, Iterable):
                continue
            for raw_phrase in items:
                if not isinstance(raw_phrase, str):
                    continue
                phrase = raw_phrase.strip().lower()
                if not phrase:
                    continue
                tokens = tuple(t for t in phrase.split() if t)
                if not tokens:
                    continue
                key = phrase
                phrases[key] = tokens
    return phrases


def _phrase_key_to_title(phrase_key: str) -> str:
    key = (phrase_key or "").lower()
    if "roas" in key:
        return "广告亏损难止（ROAS 低）"
    if "cpc" in key:
        return "点击成本飙升（CPC 高）"
    if "pixel" in key or "attribution" in key:
        return "追踪/归因不好使（Pixel/Attribution）"
    if "ad account" in key or "account" in key and ("ban" in key or "restricted" in key or "disabled" in key):
        return "广告账户被封/受限"
    if "conversion" in key:
        return "转化太低（Conversion 低）"
    return phrase_key


def _normalize_brand_candidates(
    brand_candidates: Sequence[str] | None, profile: TopicProfile
) -> tuple[str, ...]:
    if brand_candidates:
        return tuple([b.strip() for b in brand_candidates if isinstance(b, str) and b.strip()])
    # fallback: profile 的锚点/平台名
    merged = [*profile.required_entities_any, *profile.soft_required_entities_any]
    return tuple([b.strip() for b in merged if isinstance(b, str) and b.strip()])


@dataclass(frozen=True, slots=True)
class _BrandToken:
    raw: str
    needle: str


def _match_brands(text_lower: str, candidates: Sequence[str]) -> list[str]:
    tokens: list[_BrandToken] = []
    for b in candidates:
        needle = b.strip().lower()
        if not needle:
            continue
        tokens.append(_BrandToken(raw=b, needle=needle))
    matched: list[str] = []
    for tok in tokens:
        if tok.needle in text_lower:
            matched.append(tok.raw)
    # 去重并保持顺序
    seen: set[str] = set()
    out: list[str] = []
    for b in matched:
        key = b.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(b)
    return out
