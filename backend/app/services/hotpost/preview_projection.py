from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any

import yaml

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}")
_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "hotpost_quality.yaml"
_CJK_ASCII_BOUNDARY_RE = re.compile(r"([\u4e00-\u9fff])([A-Za-z0-9])|([A-Za-z0-9])([\u4e00-\u9fff])")


@lru_cache(maxsize=1)
def _load_preview_projection_config() -> dict[str, Any]:
    data = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return data.get("preview_projection") or {}


def _quote_rules() -> dict[str, Any]:
    config = _load_preview_projection_config()
    return config.get("top_quotes") if isinstance(config.get("top_quotes"), dict) else {}


def _opportunity_rules() -> dict[str, Any]:
    config = _load_preview_projection_config()
    return config.get("opportunity") if isinstance(config.get("opportunity"), dict) else {}


def _trim_text(value: Any, *, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _normalize_spacing(text: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        left_cjk, right_ascii, left_ascii, right_cjk = match.groups()
        if left_cjk and right_ascii:
            return f"{left_cjk} {right_ascii}"
        return f"{left_ascii} {right_cjk}"

    text = _CJK_ASCII_BOUNDARY_RE.sub(_repl, text)
    return re.sub(r"\s{2,}", " ", text).strip()


def _normalize_target_user(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "目标用户"

    rules = _opportunity_rules()
    replacements = rules.get("target_user_replacements") or []
    for item in replacements:
        if not isinstance(item, dict):
            continue
        needle = str(item.get("from") or "").strip()
        repl = str(item.get("to") or "").strip()
        if needle and repl:
            text = text.replace(needle, repl)
    return _normalize_spacing(text)


def _extract_tokens(text: str, *, min_length: int, stopwords: set[str]) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.lower()) if len(token) >= min_length and token not in stopwords]


def _primary_support_texts(mode: str, payload: dict[str, Any]) -> list[str]:
    if mode == "trending":
        topics = payload.get("topics") or []
        texts: list[str] = []
        for topic in topics[:2]:
            if not isinstance(topic, dict):
                continue
            texts.extend(
                str(topic.get(key) or "")
                for key in ("topic", "key_takeaway", "time_trend")
            )
            for evidence in topic.get("evidence") or []:
                if isinstance(evidence, dict):
                    texts.extend(str(evidence.get(key) or "") for key in ("title", "key_quote"))
        return texts
    if mode == "rant":
        pain_points = payload.get("pain_points") or []
        texts = []
        for point in pain_points[:2]:
            if not isinstance(point, dict):
                continue
            texts.extend(
                str(point.get(key) or "")
                for key in ("title", "description", "user_voice", "key_takeaway")
            )
            for sample in point.get("sample_quotes") or []:
                texts.append(str(sample or ""))
        return texts
    needs = payload.get("unmet_needs") or []
    market = payload.get("market_opportunity") or {}
    texts = []
    for need in needs[:2]:
        if not isinstance(need, dict):
            continue
        texts.extend(
            str(need.get(key) or "")
            for key in ("need", "opportunity_insight", "user_voice", "key_takeaway")
        )
        for workaround in need.get("current_workarounds") or []:
            if isinstance(workaround, dict):
                texts.extend(str(workaround.get(key) or "") for key in ("name", "solution"))
    if isinstance(market, dict):
        texts.extend(str(market.get(key) or "") for key in ("unmet_gap", "target_user"))
    return texts


def _rank_preview_quotes(mode: str, payload: dict[str, Any], quotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = _quote_rules()
    min_length = int(rules.get("token_min_length") or 4)
    stopwords = {str(item).strip().lower() for item in (rules.get("stopwords") or []) if str(item).strip()}
    support_limit = int(rules.get("max_support_terms") or 8)
    require_overlap = bool(rules.get("require_overlap_if_available", True))

    support_tokens = []
    for text in _primary_support_texts(mode, payload):
        support_tokens.extend(_extract_tokens(text, min_length=min_length, stopwords=stopwords))
    support = list(dict.fromkeys(support_tokens))[:support_limit]

    ranked: list[tuple[tuple[int, int, int, int], dict[str, Any]]] = []
    for quote in quotes:
        text = str(quote.get("quote") or "").strip()
        if not text:
            continue
        tokens = set(_extract_tokens(text, min_length=min_length, stopwords=stopwords))
        overlap = sum(1 for token in support if token in tokens)
        score = int(quote.get("score") or 0)
        ranked.append(((1 if overlap else 0, overlap, score, min(len(text), 180)), quote))

    if not ranked:
        return []

    ranked.sort(key=lambda item: item[0], reverse=True)
    if require_overlap and any(item[0][0] for item in ranked):
        ranked = [item for item in ranked if item[0][0]]
    return [item[1] for item in ranked]


def _preview_opportunity_recommendation(payload: dict[str, Any]) ->Optional[ str]:
    needs = payload.get("unmet_needs") or []
    market = payload.get("market_opportunity")
    if not isinstance(market, dict) or not needs or not isinstance(needs[0], dict):
        return None

    rules = _opportunity_rules()
    voice_max_chars = int(rules.get("voice_max_chars") or 96)
    need = needs[0]
    target_user = _normalize_target_user(market.get("target_user"))
    unmet_gap = str(market.get("unmet_gap") or need.get("opportunity_insight") or need.get("need") or "这个需求").strip()
    workarounds = need.get("current_workarounds") or []
    workaround = None
    if isinstance(workarounds, list) and workarounds:
        first = workarounds[0]
        if isinstance(first, dict):
            workaround = str(first.get("name") or first.get("solution") or "").strip() or None
    user_voice = _trim_text(need.get("user_voice"), max_chars=voice_max_chars)

    if workaround:
        base = f"先找{target_user}里仍在用“{workaround}”处理这个问题的人，验证“{unmet_gap}”是不是重复发生。"
    else:
        base = f"先找{target_user}验证“{unmet_gap}”是不是重复发生，再决定是否值得做自动化。"
    if user_voice:
        return f"{base} 优先复核“{user_voice}”这类场景。"
    return base


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _rant_preview_posts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for point in payload.get("pain_points") or []:
        point_data = _as_dict(point)
        for post in point_data.get("evidence_posts") or []:
            post_data = _as_dict(post)
            post_id = str(post_data.get("id") or "").strip()
            if not post_id or post_id in seen:
                continue
            seen.add(post_id)
            selected.append(post_data)
    return selected


def apply_hotpost_preview_projection(*, mode: str, state: str, payload: dict[str, Any]) -> dict[str, Any]:
    if state != "preview":
        if mode == "rant" and state == "no_hit":
            adjusted = dict(payload)
            adjusted["top_posts"] = []
            adjusted["top_rants"] = []
            next_steps = dict(adjusted.get("next_steps") or {})
            next_steps["suggested_keywords"] = []
            adjusted["next_steps"] = next_steps
            return adjusted
        return payload

    adjusted = dict(payload)
    top_quotes = adjusted.get("top_quotes")
    if isinstance(top_quotes, list) and top_quotes:
        adjusted["top_quotes"] = _rank_preview_quotes(mode, adjusted, top_quotes)

    if mode == "rant":
        preview_posts = _rant_preview_posts(adjusted)
        if not preview_posts:
            existing_posts = adjusted.get("top_posts")
            preview_posts = list(existing_posts) if isinstance(existing_posts, list) else []
        adjusted["top_posts"] = preview_posts
        adjusted["top_rants"] = preview_posts

    if mode == "opportunity":
        market = adjusted.get("market_opportunity")
        recommendation = _preview_opportunity_recommendation(adjusted)
        if isinstance(market, dict):
            market = dict(market)
            market["target_user"] = _normalize_target_user(market.get("target_user"))
            if recommendation:
                market["recommendation"] = recommendation
            adjusted["market_opportunity"] = market

    return adjusted


__all__ = ["apply_hotpost_preview_projection"]
