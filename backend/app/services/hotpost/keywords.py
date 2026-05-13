from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class HotpostLexicon:
    rant_signals: dict[str, list[str]]
    opportunity_signals: dict[str, list[str]]
    discovery_signals: dict[str, list[str]]
    intent_label: dict[str, list[str]]
    pain_categories: dict[str, list[str]]
    rant_friction_categories: dict[str, list[str]] = field(default_factory=dict)


_DEFAULT_RANT_FRICTION_CATEGORIES = {
    "trust_gap": [
        "trust",
        "scam",
        "fake",
        "misleading",
        "lied",
        "counterfeit",
        "reviews",
        "reputation",
        "不信",
        "不放心",
        "虚假",
        "骗人",
    ],
    "weak_buy_reason": [
        "sales",
        "sale",
        "purchase",
        "nobody buys",
        "conversion",
        "conversions",
        "orders",
        "traffic",
        "views",
        "value",
        "worth",
        "ads",
        "投放",
        "流量",
        "转化",
        "成交",
        "卖不动",
        "不买",
        "没人买",
        "下单",
        "订单",
    ],
    "wrong_audience": [
        "audience",
        "content",
        "targeting",
        "persona",
        "wrong people",
        "not for me",
        "人群",
        "受众",
        "定位",
    ],
    "identity_friction": [
        "privacy",
        "private",
        "discreet",
        "shame",
        "embarrassing",
        "identity",
        "隐私",
        "羞耻",
        "尴尬",
    ],
    "transaction_friction": [
        "payment",
        "refund",
        "shipping",
        "delivery",
        "checkout",
        "returns",
        "support",
        "compliance",
        "支付",
        "退款",
        "物流",
        "客服",
        "售后",
        "合规",
    ],
}


def _normalize_terms(terms: Iterable[object]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in terms:
        if raw is None:
            continue
        term = " ".join(str(raw).strip().lower().split())
        if not term or term in seen:
            continue
        seen.add(term)
        cleaned.append(term)
    return cleaned


def _normalize_group(payload: object) -> dict[str, list[str]]:
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, list[str]] = {}
    for key, terms in payload.items():
        if isinstance(terms, list | tuple | set):
            normalized[str(key)] = _normalize_terms(terms)
        elif terms is None:
            normalized[str(key)] = []
        else:
            normalized[str(key)] = _normalize_terms([terms])
    return normalized


def _load_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Hotpost keywords file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def load_hotpost_keywords(*, config_path: Path | None = None) -> HotpostLexicon:
    base_dir = Path(__file__).resolve().parents[3]
    default_path = base_dir / "config" / "boom_post_keywords.yaml"
    path = config_path or default_path
    payload = _load_yaml(path)

    rant = _normalize_group(payload.get("rant_signals", {}) or {})
    opportunity = _normalize_group(payload.get("opportunity_signals", {}) or {})
    discovery = _normalize_group(payload.get("discovery_signals", {}) or {})
    intent = _normalize_group(payload.get("intent_label", {}) or {})
    pains = _normalize_group(payload.get("pain_categories", {}) or {})
    rant_frictions = _normalize_group(
        payload.get("rant_friction_categories", {}) or _DEFAULT_RANT_FRICTION_CATEGORIES
    )

    return HotpostLexicon(
        rant_signals=rant,
        opportunity_signals=opportunity,
        discovery_signals=discovery,
        intent_label=intent,
        pain_categories=pains,
        rant_friction_categories=rant_frictions,
    )


@lru_cache
def load_default_hotpost_keywords() -> HotpostLexicon:
    return load_hotpost_keywords()


__all__ = ["HotpostLexicon", "load_hotpost_keywords", "load_default_hotpost_keywords"]
