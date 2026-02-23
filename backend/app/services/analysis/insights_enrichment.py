from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence
import os
import yaml

from app.services.community_roles import load_community_role_map
from app.utils.subreddit import normalize_subreddit_name

_DEFAULT_TREND_LABEL_MAP = {
    "🔥 EXPLODING": "爆发式增长",
    "📈 RISING": "持续升温",
    "📉 FALLING": "降温",
    "➡️ STABLE": "稳定",
}

_DEFAULT_DRIVER_RULES: list[tuple[tuple[str, ...], str]] = [
    (("expensive", "贵", "cost", "fee", "price", "fba fees", "vat", "pricing"), "透明定价与成本可控"),
    (("slow", "latency", "速度", "卡", "delay", "payout", "withdraw", "到账", "回款"), "回款速度与现金流"),
    (("multi", "multi-platform", "multi platform", "multi currency", "multi-currency", "多平台", "多币种", "跨平台", "跨币种", "wallet", "账户分散"), "多平台多币种统一管理"),
    (("confusing", "complex", "易用", "onboarding", "流程", "setup", "上手"), "易用性与自动化"),
    (("ban", "suspend", "compliance", "gdpr", "policy", "冻结", "风控"), "合规与风控稳健"),
    (("roas", "cpc", "pixel", "conversion", "转化", "投放"), "投放效果与转化提升"),
]

_DEFAULT_DRIVER_ACTIONS = {
    "透明定价与成本可控": ["费用结构透明化", "成本可预测与可对比"],
    "回款速度与现金流": ["缩短回款周期", "提高资金周转确定性"],
    "多平台多币种统一管理": ["集中管理多平台资金", "多币种对账更清晰"],
    "易用性与自动化": ["降低上手成本", "流程自动化与可视化"],
    "合规与风控稳健": ["风控规则清晰", "合规流程可执行"],
    "投放效果与转化提升": ["提高转化漏斗效率", "投放链路更可控"],
    "效率提升与省时省心": ["减少重复操作", "提升日常效率"],
}

_DEFAULT_CONFIG_PATH = Path("backend/config/insights_enrichment.yaml")
_INSIGHTS_CONFIG_CACHE: dict[str, Any] | None = None
_INSIGHTS_CONFIG_MTIME: float | None = None


def _reset_insights_config_cache() -> None:
    global _INSIGHTS_CONFIG_CACHE, _INSIGHTS_CONFIG_MTIME
    _INSIGHTS_CONFIG_CACHE = None
    _INSIGHTS_CONFIG_MTIME = None


def _load_insights_config() -> dict[str, Any]:
    global _INSIGHTS_CONFIG_CACHE, _INSIGHTS_CONFIG_MTIME
    cfg_path = Path(os.getenv("INSIGHTS_ENRICHMENT_CONFIG_PATH", str(_DEFAULT_CONFIG_PATH)))
    if cfg_path.exists():
        mtime = cfg_path.stat().st_mtime
        if _INSIGHTS_CONFIG_CACHE is not None and _INSIGHTS_CONFIG_MTIME == mtime:
            return _INSIGHTS_CONFIG_CACHE
        try:
            payload = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            if isinstance(payload, dict):
                _INSIGHTS_CONFIG_CACHE = payload
                _INSIGHTS_CONFIG_MTIME = mtime
                return payload
        except Exception:
            return {}
    _INSIGHTS_CONFIG_CACHE = {}
    _INSIGHTS_CONFIG_MTIME = None
    return {}


def _get_trend_label_map() -> Mapping[str, str]:
    cfg = _load_insights_config()
    mapping = cfg.get("trend_label_map")
    if isinstance(mapping, dict) and mapping:
        return {str(k): str(v) for k, v in mapping.items()}
    return _DEFAULT_TREND_LABEL_MAP


def _get_driver_rules() -> list[tuple[tuple[str, ...], str]]:
    cfg = _load_insights_config()
    raw_rules = cfg.get("driver_rules") or []
    parsed: list[tuple[tuple[str, ...], str]] = []
    for item in raw_rules:
        if not isinstance(item, Mapping):
            continue
        keywords = item.get("keywords") or []
        label = str(item.get("driver") or "").strip()
        if not label:
            continue
        keywords_list = [str(k).strip().lower() for k in keywords if str(k).strip()]
        if not keywords_list:
            continue
        parsed.append((tuple(keywords_list), label))
    if parsed:
        return parsed
    return _DEFAULT_DRIVER_RULES


def _get_driver_actions() -> Mapping[str, Sequence[str]]:
    cfg = _load_insights_config()
    actions = cfg.get("driver_actions")
    if isinstance(actions, dict) and actions:
        return {str(k): list(v or []) for k, v in actions.items()}
    return _DEFAULT_DRIVER_ACTIONS


def summarize_trend_series(
    series: Sequence[Mapping[str, Any]],
    *,
    degraded: bool,
    sources: Sequence[str] | None,
) -> dict[str, Any]:
    if not series:
        return {"label": "N/A", "reason": "暂无趋势数据", "series": []}

    last = series[-1]
    trend_label = str(last.get("trend") or "")
    label = _get_trend_label_map().get(trend_label, "稳定")
    count = int(last.get("count") or 0)
    growth = last.get("growth_rate")
    velocity = last.get("recent_velocity")

    growth_txt = "N/A"
    if isinstance(growth, (int, float)):
        growth_txt = f"{growth:.0%}"

    velocity_txt = None
    if isinstance(velocity, (int, float)):
        velocity_txt = f"{velocity:.2f}"

    reason = f"近一月讨论量 {count}，环比 {growth_txt}"
    if velocity_txt:
        reason = f"{reason}，近三月速度系数 {velocity_txt}"

    if degraded:
        suffix = "趋势数据不完整"
        if sources:
            suffix = f"{suffix}（{', '.join([str(s) for s in sources])}）"
        reason = f"{reason}；{suffix}"

    return {"label": label, "reason": reason, "series": list(series)}


def classify_overall_saturation(value: float) -> str:
    if value >= 0.6:
        return "高饱和"
    if value >= 0.2:
        return "中等"
    return "机会窗口"


def build_market_saturation_payload(rows: Sequence[Any], *, top_brands: int = 3) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        overall = float(getattr(row, "overall_saturation", 0.0) or 0.0)
        brands = getattr(row, "brands", []) or []
        top = []
        for brand in list(brands)[:top_brands]:
            top.append(
                {
                    "brand": str(getattr(brand, "brand", "")),
                    "saturation": round(float(getattr(brand, "saturation", 0.0) or 0.0), 2),
                    "status": str(getattr(brand, "status", "中等")),
                }
            )
        payload.append(
            {
                "community": str(getattr(row, "community", "")),
                "overall_saturation": round(overall, 2),
                "status": classify_overall_saturation(overall),
                "top_brands": top,
            }
        )
    return payload


def derive_driver_label(description: str) -> str:
    text = (description or "").lower()
    for keywords, label in _get_driver_rules():
        if any(keyword in text for keyword in keywords):
            return label
    return "效率提升与省时省心"


def build_top_drivers(
    pain_points: Sequence[Mapping[str, Any]],
    *,
    action_items: Sequence[Mapping[str, Any]] | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    driver_counts: Counter[str] = Counter()
    driver_pains: dict[str, list[str]] = defaultdict(list)

    for pain in pain_points:
        desc = str(pain.get("description") or "").strip()
        if not desc:
            continue
        weight = int(pain.get("frequency") or 1)
        label = derive_driver_label(desc)
        driver_counts[label] += max(weight, 1)
        if desc not in driver_pains[label]:
            driver_pains[label].append(desc)

    ranked = sorted(driver_counts.items(), key=lambda item: (-item[1], item[0]))
    out: list[dict[str, Any]] = []
    for label, _count in ranked[:limit]:
        pains = driver_pains.get(label, [])
        rationale = "高频痛点集中在：" + " / ".join(pains[:2]) if pains else "暂无明确痛点依据"
        actions = _get_driver_actions().get(label, [])
        if not actions and action_items:
            actions = [
                str(item.get("problem_definition") or "").strip()
                for item in action_items
                if item.get("problem_definition")
            ][:2]
        out.append(
            {
                "title": label,
                "description": rationale,
                "rationale": rationale,
                "actions": list(actions),
                "source_pains": pains[:3],
            }
        )
    return out


def _pick_persona(community: str, categories: Sequence[str]) -> str:
    role_map = load_community_role_map()
    role = role_map.get(normalize_subreddit_name(community))
    if role:
        if role == "operations":
            return "卖家运营/增长党"
        return f"{role}人群"

    normalized = [str(c).lower() for c in categories if c]
    if any("seller" in c or "ops" in c for c in normalized):
        return "卖家运营/增长党"
    return "用户需求/消费党"


def build_battlefield_profiles(
    *,
    communities_detail: Sequence[Mapping[str, Any]],
    pain_points: Sequence[Mapping[str, Any]],
    pain_counts_by_community: Mapping[str, int] | None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []

    pain_counts_by_community = pain_counts_by_community or {}
    scored: list[tuple[tuple[int, int], Mapping[str, Any]]] = []
    for detail in communities_detail:
        name = str(detail.get("name") or "").strip()
        if not name:
            continue
        normalized = normalize_subreddit_name(name)
        mentions = int(detail.get("mentions") or 0)
        pain_hits = int(pain_counts_by_community.get(name) or pain_counts_by_community.get(normalized) or 0)
        scored.append(((pain_hits, mentions), detail))

    scored.sort(
        key=lambda item: (
            -item[0][0],
            -item[0][1],
            str(item[1].get("name") or ""),
        )
    )
    profiles: list[dict[str, Any]] = []

    for _score_tuple, detail in scored[:limit]:
        name = str(detail.get("name") or "").strip()
        normalized = normalize_subreddit_name(name)
        categories = detail.get("categories") or []
        persona = _pick_persona(name, categories)

        matched_pains: list[tuple[int, str]] = []
        evidence_posts: list[Mapping[str, Any]] = []
        for pain in pain_points:
            desc = str(pain.get("description") or "").strip()
            if not desc:
                continue
            examples = pain.get("example_posts") or []
            matched = False
            for ex in examples:
                if normalize_subreddit_name(str(ex.get("community") or "")) == normalized:
                    matched = True
                    if ex not in evidence_posts:
                        evidence_posts.append(ex)
            if matched:
                matched_pains.append((int(pain.get("frequency") or 0), desc))

        if not matched_pains:
            matched_pains = [
                (int(pain.get("frequency") or 0), str(pain.get("description") or "").strip())
                for pain in pain_points
                if pain.get("description")
            ]

        matched_pains.sort(key=lambda item: (-item[0], item[1]))
        pain_focus = [desc for _, desc in matched_pains[:3] if desc]

        drivers = [derive_driver_label(desc) for desc in pain_focus if desc]
        strategy = []
        for driver in drivers:
            for action in _get_driver_actions().get(driver, []):
                if action not in strategy:
                    strategy.append(action)
            if len(strategy) >= 3:
                break

        profiles.append(
            {
                "communities": [name],
                "persona": persona,
                "pain_focus": pain_focus,
                "strategy": strategy,
                "evidence_posts": list(evidence_posts)[:5],
            }
        )
    return profiles


__all__ = [
    "summarize_trend_series",
    "classify_overall_saturation",
    "build_market_saturation_payload",
    "derive_driver_label",
    "build_top_drivers",
    "build_battlefield_profiles",
]
