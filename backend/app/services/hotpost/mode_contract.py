from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any

import yaml

from app.schemas.hotpost import Hotpost
from app.services.hotpost.evidence_focus import HotpostEvidenceFocusContext, has_domain_anchor


@dataclass(frozen=True)
class _Rules:
    min_evidence_posts: int
    min_anchor_posts: int
    min_strong_quotes: int
    min_primary_items: int


@dataclass(frozen=True)
class _Projection:
    primary_list_field: str
    preview_item_limit: int
    standard_item_limit: int
    preview_quote_limit: int
    standard_quote_limit: int
    min_quote_chars: int
    clear_fields_on_no_hit: list[str]


@dataclass(frozen=True)
class _Contract:
    hit_rules: _Rules
    sufficiency_rules: _Rules
    projection: _Projection


def _load_yaml() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / "config" / "hotpost_quality.yaml"
    with path.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh) or {}
    return payload if isinstance(payload, dict) else {}


def _as_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _build_rules(payload:Optional[ dict[str, Any]], *, default_posts: int, default_items: int) -> _Rules:
    data = dict(payload or {})
    return _Rules(
        min_evidence_posts=_as_int(data.get("min_evidence_posts"), default_posts),
        min_anchor_posts=_as_int(data.get("min_anchor_posts"), 0),
        min_strong_quotes=_as_int(data.get("min_strong_quotes"), 0),
        min_primary_items=_as_int(data.get("min_primary_items"), default_items),
    )


def _build_projection(payload:Optional[ dict[str, Any]]) -> _Projection:
    data = dict(payload or {})
    return _Projection(
        primary_list_field=str(data.get("primary_list_field") or "").strip(),
        preview_item_limit=_as_int(data.get("preview_item_limit"), 1),
        standard_item_limit=_as_int(data.get("standard_item_limit"), 3),
        preview_quote_limit=_as_int(data.get("preview_quote_limit"), 2),
        standard_quote_limit=_as_int(data.get("standard_quote_limit"), 3),
        min_quote_chars=_as_int(data.get("min_quote_chars"), 24),
        clear_fields_on_no_hit=_as_list(data.get("clear_fields_on_no_hit")),
    )


@lru_cache
def load_hotpost_mode_contracts() -> dict[str, _Contract]:
    payload = dict(_load_yaml().get("mode_contracts") or {})
    defaults = {"trending": (2, 1), "rant": (2, 1), "opportunity": (1, 1)}
    contracts: dict[str, _Contract] = {}
    for mode, (default_posts, default_items) in defaults.items():
        data = dict(payload.get(mode) or {})
        contracts[mode] = _Contract(
            hit_rules=_build_rules(data.get("hit_rules"), default_posts=default_posts, default_items=default_items),
            sufficiency_rules=_build_rules(
                data.get("sufficiency_rules"),
                default_posts=default_posts + 2,
                default_items=default_items + 1,
            ),
            projection=_build_projection(data.get("projection_rules")),
        )
    return contracts


def _count_primary_items(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    return len(value) if isinstance(value, list) else 0


def _count_strong_quotes(payload: dict[str, Any], *, min_quote_chars: int) -> int:
    quotes = payload.get("top_quotes")
    if not isinstance(quotes, list):
        return 0
    return sum(1 for item in quotes if isinstance(item, dict) and len(str(item.get("quote") or "").strip()) >= min_quote_chars)


def _count_anchor_posts(top_posts: list[Hotpost], *, positive_terms: list[str], domain_terms: list[str]) -> int:
    if not top_posts:
        return 0
    if not (positive_terms or domain_terms):
        return len(top_posts)
    context = HotpostEvidenceFocusContext(
        query_terms=[],
        intent_terms=list(positive_terms),
        domain_terms=list(domain_terms),
        focus_terms_limit=4,
    )
    count = 0
    for post in top_posts:
        if has_domain_anchor(context=context, text_blobs=[post.title, post.body_preview, post.subreddit]):
            count += 1
    return count


def _mode_note(
    mode: str,
    state: str,
    *,
    evidence_count: int,
    reasons: list[str],
    raw_posts:Optional[ int] = None,
    relevance_filtered:Optional[ int] = None,
    relevant_posts:Optional[ int] = None,
    voice_hits:Optional[ int] = None,
) -> str:
    raw_total = max(int(raw_posts or 0), evidence_count)
    relevance_gap = max(0, int(relevance_filtered or 0))
    relevant_total = max(int(relevant_posts or 0), evidence_count)
    strong_voice_total = max(0, int(voice_hits or 0))

    if state == "no_hit":
        if "hit:evidence_posts" in reasons:
            if raw_total > relevant_total and relevance_gap >= relevant_total:
                return (
                    f"这次抓到 {raw_total} 条帖子，但真正高相关只有 {relevant_total} 条，"
                    f"当前更像命中偏了，先不给完整 {mode} 结论。"
                )
            return f"这次只抓到 {relevant_total} 条高相关帖子，能直接支撑这个问题的证据还不够，先不给完整 {mode} 结论。"
        if "hit:strong_quotes" in reasons and relevant_total:
            return (
                f"高相关帖子已有 {relevant_total} 条，但能直接拿来当原话的强证据只有 {strong_voice_total} 条，"
                f"先不给完整 {mode} 结论。"
            )
        if any(
            reason in reasons
            for reason in ("hit:anchor_posts", "hit:strong_quotes", "hit:primary_items")
        ):
            return (
                f"帖子不是完全没有，但能直接支撑这个问题的原话和主证据还不够，"
                f"先不给完整 {mode} 结论。"
            )
        return f"当前只命中 {evidence_count} 条弱相关证据，暂不输出完整 {mode} 结论。"

    if state == "preview":
        if "preview:evidence_posts" in reasons:
            if raw_total > relevant_total and relevance_gap >= relevant_total:
                return (
                    f"这次抓到 {raw_total} 条帖子，但真正高相关只有 {relevant_total} 条，"
                    "当前更像命中偏了，先只保留最强信号。"
                )
            return f"这次只抓到 {relevant_total} 条高相关帖子，先保留最强信号。"
        if "preview:strong_quotes" in reasons and relevant_total:
            return (
                f"高相关帖子已有 {relevant_total} 条，但能直接拿来当原话的强证据只有 {strong_voice_total} 条，"
                "先只保留最强信号。"
            )
        if any(
            reason in reasons
            for reason in ("preview:anchor_posts", "preview:strong_quotes", "preview:primary_items")
        ):
            return "帖子已经抓到一些，但能直接支撑主判断的原话和主证据还不够，先只保留最强信号。"
        return f"当前命中 {evidence_count} 条相关证据，先保留最强信号。"

    return f"当前结论基于已命中的 {evidence_count} 条相关证据。"


def _trim_list(payload: dict[str, Any], field: str, limit: int) -> None:
    value = payload.get(field)
    if isinstance(value, list) and limit > 0:
        payload[field] = value[:limit]


def _clear_field(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    payload[field] = [] if isinstance(value, list) else None


def apply_hotpost_mode_contract(
    *,
    mode: str,
    payload: dict[str, Any],
    top_posts: list[Hotpost],
    positive_intent_terms: list[str],
    domain_terms: list[str],
    raw_posts:Optional[ int] = None,
    relevance_filtered:Optional[ int] = None,
    relevant_posts:Optional[ int] = None,
) -> tuple[dict[str, Any], str, list[str], str, dict[str, int]]:
    contract = load_hotpost_mode_contracts().get(mode)
    if contract is None:
        metrics = {
            "evidence_posts": len(top_posts),
            "anchor_posts": len(top_posts),
            "strong_quotes": _count_strong_quotes(payload, min_quote_chars=24),
            "primary_items": 0,
        }
        return payload, "standard", [], _mode_note(
            mode,
            "standard",
            evidence_count=len(top_posts),
            reasons=[],
            raw_posts=raw_posts,
            relevance_filtered=relevance_filtered,
            relevant_posts=relevant_posts,
            voice_hits=metrics["strong_quotes"],
        ), metrics

    evidence_count = len(top_posts)
    primary_items = _count_primary_items(payload, contract.projection.primary_list_field)
    strong_quotes = _count_strong_quotes(payload, min_quote_chars=contract.projection.min_quote_chars)
    anchor_posts = _count_anchor_posts(
        top_posts,
        positive_terms=positive_intent_terms,
        domain_terms=domain_terms,
    )
    reasons: list[str] = []
    metrics = {
        "evidence_posts": evidence_count,
        "anchor_posts": anchor_posts,
        "strong_quotes": strong_quotes,
        "primary_items": primary_items,
    }

    for key, value in metrics.items():
        if value < getattr(contract.hit_rules, f"min_{key}"):
            reasons.append(f"hit:{key}")
    if reasons:
        for field in contract.projection.clear_fields_on_no_hit:
            _clear_field(payload, field)
        return payload, "no_hit", reasons, _mode_note(
            mode,
            "no_hit",
            evidence_count=evidence_count,
            reasons=reasons,
            raw_posts=raw_posts,
            relevance_filtered=relevance_filtered,
            relevant_posts=relevant_posts,
            voice_hits=metrics["strong_quotes"],
        ), metrics

    preview_reasons = [f"preview:{key}" for key, value in metrics.items() if value < getattr(contract.sufficiency_rules, f"min_{key}")]
    state = "preview" if preview_reasons else "standard"
    item_limit = contract.projection.preview_item_limit if state == "preview" else contract.projection.standard_item_limit
    quote_limit = contract.projection.preview_quote_limit if state == "preview" else contract.projection.standard_quote_limit
    _trim_list(payload, contract.projection.primary_list_field, item_limit)
    _trim_list(payload, "top_quotes", quote_limit)
    return payload, state, preview_reasons, _mode_note(
        mode,
        state,
        evidence_count=evidence_count,
        reasons=preview_reasons,
        raw_posts=raw_posts,
        relevance_filtered=relevance_filtered,
        relevant_posts=relevant_posts,
        voice_hits=metrics["strong_quotes"],
    ), metrics


__all__ = ["apply_hotpost_mode_contract", "load_hotpost_mode_contracts"]
