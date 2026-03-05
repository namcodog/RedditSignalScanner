#!/usr/bin/env python3
"""
Template-driven T1 Market Report:
- 固定骨架（决策卡4、概览、战场4、痛点3、驱动力3、机会卡2、顶部信息）
- 话题/赛道动态：通过参数/环境传入，不硬编码
- 有 OPENAI_API_KEY 用 LLM，没 Key 输出降级版（同骨架，标记降级）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any, Iterable, Tuple, Optional
import yaml

from app.core.config import settings
from app.db.session import SessionFactory
from app.services.llm.clients.openai_client import OpenAIChatClient
from app.services.analysis.deduplicator import deduplicate_posts
from app.services.analysis.opportunity_scorer import OpportunityScorer
from app.services.analysis.scoring_rules import ScoringRulesLoader
from app.services.analysis import (
    assign_competitor_layers,
    build_layer_summary,
    QuoteExtractor,
    extract_keywords,
)
from app.services.analysis.persona_generator import PersonaGenerator
from app.services.analysis.community_ranker import compute_ranking_scores
from app.services.analysis.saturation_matrix import SaturationMatrix
from app.services.analysis.signal_extraction import SignalExtractor
from app.services.analysis.pain_cluster import cluster_pain_points_auto
from app.services.facts_v2.midstream import (
    compute_brand_pain_v2,
    compute_pain_clusters_v2,
    compute_source_range,
    filter_solutions_by_profile,
)
from app.services.facts_v2.quality import quality_check_facts_v2
from app.services.analysis.t1_stats import (
    build_stats_snapshot,
    build_trend_analysis,
    build_entity_sentiment_matrix,
    fetch_topic_relevant_communities,
    write_snapshot_to_file,
)
from app.services.community.blacklist_loader import BlacklistConfig
from app.services.labeling.comments_labeling import classify_and_label_comments
from app.services.labeling.labeling_posts import label_posts_recent
from app.services.analysis.topic_profiles import (
    TopicProfile,
    build_fetch_keywords,
    build_search_keywords,
    filter_items_by_profile_context,
    filter_relevance_map_with_profile,
    load_topic_profiles,
    match_topic_profile,
    normalize_subreddit,
    topic_profile_allows_community,
    topic_profile_blocklist_keywords,
)
from app.utils.url import normalize_reddit_url
from app.services.semantic.text_classifier import classify_category_aspect
from app.models.comment import Category
from sqlalchemy import text
from sqlalchemy.engine import Result
import hashlib
import uuid
from copy import deepcopy


REPORT_SYSTEM_PROMPT_V2 = '''[System]

你是一名懂电商、懂 Reddit、也懂人话的“市场洞察分析师”。

【你的输入】
- product_desc：这次要研究的问题/赛道描述。
- facts：已经清洗好的事实包（来自 Reddit T1 社区），内容包括但不限于：
  - 讨论量、时间趋势（哪些话题在升温/降温）
  - 不同人群类型占比（吐槽/避坑党、找货/工具党、进阶/学习党）
  - 不同痛点类型的占比和强度
  - 品牌/平台/渠道在讨论中的出现频率和情绪
  - P/S Ratio（问题帖 : 解决帖）
  - business_signals（high_value_pains, buying_opportunities, competitor_insights, market_saturation 等）
  - sample_comments_db（带链接的真实评论样本）

你只根据 facts 说话，不能脑补 facts 里不存在的结论。

------------------------------------------------
【铁律：写什么，不写什么】

A. 禁止假装在看销量/财报  
- 禁用词（以及类似说法）：  
  “市场份额 / 占有率 / 营收 / 销量 / 主导者 / 挑战者 / 瓜分市场”。  
- 只能用“讨论维度”的说法，比如：  
  “讨论热度高 / 提及占比高 / 声量大 / 在 Reddit 上被提到更多”。

B. 禁止暴露 JSON 字段名 / 变量名  
- 正文里绝对不要出现：aspect_breakdown, need_distribution, brand_pain, market_landscape, pain_hierarchy 等字段名。  
- 要说：“从痛点分布来看… / 从不同人群的需求占比来看… / 从品牌和问题的关联上看…”。

C. 用户类型一律用“xxx党”  
- Survival → “吐槽/避坑党”：出问题、来抱怨、求安慰、求解救的人。  
- Efficiency → “找货/工具党”：来问“用啥好 / 有啥推荐 / 哪个更划算”的人。  
- Growth → “进阶/学习党”：看教程、学玩法、分享经验的人。  
- 禁止写“生存型用户 / 效率型用户 / 成长型用户”。

D. 术语翻译  
- subscription → “订阅服务 / 月费模式”  
- content → 结合语境改成“教程 / 食谱 / 说明书 / 使用攻略”等具体说法  
- install → “安装和设置过程 / 安装麻烦不麻烦”  
- EXPLODING → “爆发式增长”（只在描述趋势时用）  
- P/S Ratio → 可以保留写法，但必须用一句人话解释它是什么。

E. 数据不足时的写法  
- 不要写：“由于缺乏数据，无法判断 / 样本不足所以不确定”这类废话。  
- 可以：  
  - 直接略过某个细分点，或者  
  - 写成：“从目前能看到的这批讨论里，大家更常提到的是……”

------------------------------------------------
【使用 facts 的原则】

1. 把 facts 当作经过聚合后的“事实表”，不能凭感觉扩展。任何痛点、机会、结论，都必须能在 facts 的字段里找到依据（尤其是 business_signals、market_saturation、extracted_keywords 和 sample_comments_db）。  
2. 每个“重点痛点”在正文里至少要能对应到 1 条真实讨论链接（来自 sample_comments_db）。  
3. 不要引用具体 JSON key 名称，但要忠实使用其中的结构：  
   - 比如：用 pain_tree 推断“表层抱怨”背后的成因链。  
4. 所有结论最后都要落回一句话：“这对用户的下一步决策有什么用”。

------------------------------------------------
【报告结构总览】

完整报告固定 7 个模块：
1. 顶部信息  
2. 决策卡片（4 组）  
   2.1 需求趋势  
   2.2 需求图谱透视（人群结构）  
   2.3 P/S Ratio 大白话  
   2.4 高潜力社群  
3. 概览（市场健康度）  
   3.1 竞争格局（平台 / 品牌 / 信息渠道）  
   3.2 P/S Ratio 深度解读  
4. 核心战场推荐（3–4 个社区画像）  
5. 用户痛点（3 个）  
6. Top 购买 / 决策驱动力（2–3 条）  
7. 商业机会（2 张机会卡）

一次调用只负责其中一部分内容，由 user 指令里的 output_part 决定：
- output_part = "part1" → 只写模块 1–4  
- output_part = "part2" → 只写模块 5–7  

写作风格：  
- 全程大白话，少用抽象词。  
- 先说结论，再给 2–3 个“凭啥这么说”的依据（基于 facts）。  
- 不要凑字数，内容宁可少，但每一句都要有用。'''


def _normalize_subreddit(name: str) -> str:
    return name.lower().removeprefix("r/")


PLATFORMS = {
    "amazon",
    "shopify",
    "aliexpress",
    "ebay",
    "walmart",
}
CHANNELS = {"youtube", "reddit", "tiktok", "instagram", "facebook"}
NOISE_TERMS = {"price", "prices", "video", "videos"}
EDC_CORE_COMMUNITIES = [
    "r/flashlight",
    "r/flashlights",
    "r/edc",
    "r/edcexchange",
    "r/flashlight_builds",
    "r/flashlight_mods",
]
OPS_CORE_COMMUNITIES = {
    "r/amazonfba",
    "r/amazonseller",
    "r/fulfillmentbyamazon",
    "r/amazonflexdrivers",
    "r/amazonprime",
    "r/amazonvine",
    "r/amazon",
}
OPS_EXCLUDE_COMMUNITIES = {
    "r/frugal",
    "r/financialindependence",
    "r/povertyfinance",
    "r/personalfinance",
    "r/churning",
    "r/buyitforlife",
    "r/askwomen",
    "r/relationships",
    "r/relationship_advice",
    "r/marketing",
    "r/ecommerce",
    "r/entrepreneur",
    "r/aliexpress",
    "r/etsy",
    "r/shopify",
    "r/flipping",
    "r/smallbusiness",
    "r/printondemand",
    "r/startups",
    "r/childfree",
    "r/homeowners",
    "r/shopifyecommerce",
    "r/dropshipping",
    "r/etsy",
}
DEFAULT_CONFIG_PATH = Path("config") / "vertical_overrides.yaml"


def _load_vertical_overrides(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover
        print(f"⚠️ vertical_overrides config load failed: {exc}")
        return {}


VERTICAL_OVERRIDES = _load_vertical_overrides()
DEFAULTS_CFG = VERTICAL_OVERRIDES.get("defaults", {})


def _load_topic_profiles(path: Path = Path("backend/config/topic_profiles.yaml")) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data.get("topic_profiles", [])
    except Exception as e:
        print(f"⚠️ Failed to load topic profiles: {e}")
        return []


def _match_topic_profile(topic: str, profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find a matching profile by id or topic_name."""
    t_lower = topic.strip().lower()
    for p in profiles:
        if p.get("id") == t_lower or p.get("topic_name", "").lower() == t_lower:
            return p
    return None


# Base defaults (kept for backward compatibility if config missing)
MIN_TOPIC_HITS = 5
MAX_OFFTOPIC_RATIO = 0.35
SEMANTIC_SIM_THRESHOLD = 0.38  # pgvector <=> distance threshold for semantic match
MAX_DYNAMIC_WHITELIST = 10
MAX_DYNAMIC_BLACKLIST = 20

# Override tunables with config defaults (behavior-equivalent when config missing)
MIN_TOPIC_HITS = DEFAULTS_CFG.get("min_topic_hits", MIN_TOPIC_HITS)
MAX_OFFTOPIC_RATIO = DEFAULTS_CFG.get("max_offtopic_ratio", MAX_OFFTOPIC_RATIO)
SEMANTIC_SIM_THRESHOLD = DEFAULTS_CFG.get("semantic_sim_threshold", SEMANTIC_SIM_THRESHOLD)
MAX_DYNAMIC_WHITELIST = DEFAULTS_CFG.get("dynamic_whitelist_cap", MAX_DYNAMIC_WHITELIST)
MAX_DYNAMIC_BLACKLIST = DEFAULTS_CFG.get("dynamic_blacklist_cap", MAX_DYNAMIC_BLACKLIST)
QUALITY_THRESHOLDS = DEFAULTS_CFG.get(
    "quality",
    {"comments_min": 60, "posts_min": 30, "solutions_min": 5, "coverage_min": 5},
)
COMMENTS_CFG = DEFAULTS_CFG.get(
    "comments",
    {
        "limit": 150,
        "per_sub_cap": 40,
        "fallback_threshold": 60,
        "fallback_limit": 180,
        "fallback_days": 540,
        "fallback_min_len_other": 80,
    },
)
POSTS_CFG = DEFAULTS_CFG.get(
    "posts",
    {
        "limit": 60,
        "fallback_limit": 80,
        "fallback_days": 540,
    },
)
SOLUTIONS_CFG = DEFAULTS_CFG.get(
    "solutions",
    {
        "sentiment_primary": -0.05,
        "sentiment_secondary": -0.15,
        "sentiment_tertiary": -0.2,
        "dedup_threshold": 0.75,
    },
)


def _get_vertical_cfg(vertical: str) -> dict[str, Any]:
    return VERTICAL_OVERRIDES.get("verticals", {}).get(vertical or "", {})


def _hash_config(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()
    except Exception:
        return ""


def _hash_files(paths: Iterable[Path]) -> str:
    sha = hashlib.sha256()
    for p in paths:
        if not p.exists():
            continue
        try:
            sha.update(p.read_bytes())
        except Exception:
            continue
    return sha.hexdigest()


async def _write_quality_audit(
    session: Any,
    *,
    run_id: str,
    args: argparse.Namespace,
    config_hash: str,
    time_window_used: int,
    trend_source: str,
    trend_degraded: bool,
    quality: dict[str, Any],
    insufficient_flags: list[str],
    dynamic_whitelist: set[str],
    dynamic_blacklist: set[str],
) -> None:
    try:
        await session.execute(
            text(
                """
                INSERT INTO facts_quality_audit (
                    run_id, topic, days, mode, config_hash,
                    trend_source, trend_degraded, time_window_used,
                    comments_count, posts_count, solutions_count, community_coverage,
                    degraded, data_fallback, posts_fallback, solutions_fallback,
                    dynamic_whitelist, dynamic_blacklist, insufficient_flags
                )
                VALUES (
                    :run_id, :topic, :days, :mode, :config_hash,
                    :trend_source, :trend_degraded, :time_window_used,
                    :comments_count, :posts_count, :solutions_count, :community_coverage,
                    :degraded, :data_fallback, :posts_fallback, :solutions_fallback,
                    :dynamic_whitelist, :dynamic_blacklist, :insufficient_flags
                )
                ON CONFLICT (run_id) DO NOTHING
                """
            ),
            {
                "run_id": run_id,
                "topic": args.topic,
                "days": args.days,
                "mode": args.mode,
                "config_hash": config_hash,
                "trend_source": trend_source,
                "trend_degraded": trend_degraded,
                "time_window_used": time_window_used,
                "comments_count": quality.get("comments_count"),
                "posts_count": quality.get("posts_count"),
                "solutions_count": quality.get("solutions_count"),
                "community_coverage": quality.get("community_coverage"),
                "degraded": quality.get("degraded"),
                "data_fallback": quality.get("data_fallback"),
                "posts_fallback": quality.get("posts_fallback"),
                "solutions_fallback": quality.get("solutions_fallback"),
                "dynamic_whitelist": json.dumps(sorted(list(dynamic_whitelist)), ensure_ascii=False),
                "dynamic_blacklist": json.dumps(sorted(list(dynamic_blacklist)), ensure_ascii=False),
                "insufficient_flags": json.dumps(insufficient_flags, ensure_ascii=False),
            },
        )
        await session.commit()
        print("🧾 facts_quality_audit inserted.")
    except Exception as exc:  # pragma: no cover
        print(f"⚠️ quality audit insert failed (ignored): {exc}")

# Off-topic cues per vertical to drive dynamic contextual filtering
VERTICAL_OFFTOPIC = {
    "pets": {"kitchen", "cook", "cooking", "recipe", "frugal", "budget", "cleaning", "coupon"},
    "home_kitchen": {"pets", "cat", "dog", "litter", "fish", "aquarium"},
    "beauty": {"workout", "gym", "finance", "job"},
    "consumer_electronics": {"frugal", "budget", "coupon", "finance", "personalfinance"},
    "edc": {"frugal", "budget", "coupon", "finance", "personalfinance"},
}
# Hard-coded vertical whitelists/blacklists — kept for backward compatibility; config overrides at runtime
VERTICAL_CORE_WHITELIST = {
    "pets": {"r/cats", "r/catcare", "r/litterrobot", "r/litterboxes", "r/pets", "r/catadvice", "r/catowners"},
    "consumer_electronics": {"r/gadgets", "r/flashlight", "r/flashlights", "r/edc", "r/edcexchange", "r/flashlight_builds", "r/flashlight_mods"},
    "edc": {"r/flashlight", "r/flashlights", "r/edc", "r/edcexchange", "r/flashlight_builds", "r/flashlight_mods"},
    "home_kitchen": {"r/coffee", "r/espresso", "r/pourover", "r/barista"},
    "operations": {"r/amazonfba", "r/amazonseller", "r/fulfillmentbyamazon", "r/amazonprime", "r/amazonflexdrivers", "r/amazonvine"},
}
VERTICAL_CORE_BLACKLIST = {
    "consumer_electronics": {"r/financialindependence", "r/frugal", "r/povertyfinance", "r/personalfinance"},
    "edc": {"r/financialindependence", "r/frugal", "r/povertyfinance", "r/personalfinance"},
}

def _classify_entity(name: str) -> str:
    normalized = (name or "").strip().lower()
    if not normalized:
        return "potential_brand"
    if normalized in PLATFORMS:
        return "platform"
    if normalized in CHANNELS:
        return "channel"
    if normalized in NOISE_TERMS:
        return "noise"
    return "potential_brand"


def _compute_trend_labels_from_counts(series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """局部重用 t1_stats 的趋势标签逻辑，避免重复 SQL 时重算。"""
    results: list[dict[str, Any]] = []
    prev = None
    recent_velocity = 1.0
    if len(series) >= 3:
        l30 = series[-1]["count"]
        l90 = sum(s["count"] for s in series[-3:])
        if l90 > 0:
            recent_velocity = (3.0 * l30) / l90
    for entry in series:
        cnt = entry["count"]
        if prev is None or prev == 0:
            growth = None if prev is None else (cnt - prev) / max(1, prev)
        else:
            growth = (cnt - prev) / prev
        if growth is None:
            trend_label = "➡️ STABLE"
        elif (growth > 0.5 and cnt > 5) or (recent_velocity > 1.3 and cnt > 10):
            trend_label = "🔥 EXPLODING"
        elif growth > 0.2 or recent_velocity > 1.1:
            trend_label = "📈 RISING"
        elif growth < -0.2 or recent_velocity < 0.8:
            trend_label = "📉 FALLING"
        else:
            trend_label = "➡️ STABLE"
        results.append(
            {
                "month": entry["month"],
                "count": cnt,
                "growth_rate": None if growth is None else round(growth, 4),
                "trend": trend_label,
            }
        )
        prev = cnt
    if results:
        results[-1]["recent_velocity"] = round(recent_velocity, 2)
    return results


async def _load_trend_with_fallback(
    session: Any,
    topic_tokens: list[str],
    days: int,
) -> tuple[list[dict[str, Any]], str, int, bool]:
    """
    优先使用原逻辑 (build_trend_analysis)；长窗/异常时降级为 MV（无 topic 过滤）。
    返回: (trend_data, trend_source, time_window_used, trend_degraded)
    """
    months = max(1, min(24, (days + 29) // 30))
    prefer_mv = months > 12
    mv_error: Exception | None = None

    if prefer_mv:
        try:
            sql = text(
                """
                SELECT to_char(month_start, 'YYYY-MM') AS month_key,
                       COALESCE(posts_cnt,0)::bigint + COALESCE(comments_cnt,0)::bigint AS cnt
                FROM mv_monthly_trend
                WHERE month_start >= date_trunc('month', now()) - (interval '1 month' * :months)
                ORDER BY month_start
                """
            )
            rows = await session.execute(sql, {"months": months})
            series = [{"month": row.month_key, "count": int(row.cnt or 0)} for row in rows.fetchall()]
            trend = _compute_trend_labels_from_counts(series)
            time_window_used = months * 30
            # MV 命中即视为可用，不降级；来源标注为 mv_monthly_trend
            return trend, "mv_monthly_trend", time_window_used, False
        except Exception as exc:  # pragma: no cover
            mv_error = exc
            print(f"⚠️ Trend MV preferred path failed, fallback to runtime: {exc}")

    try:
        trend = await build_trend_analysis(session, topic_tokens=topic_tokens, months=months)
        return trend, "runtime_topic_filtered", months * 30, False
    except Exception as exc:  # pragma: no cover
        print(f"⚠️ Trend runtime failed, fallback to mv_monthly_trend: {exc}")
        try:
            sql = text(
                """
                SELECT to_char(month_start, 'YYYY-MM') AS month_key,
                       COALESCE(posts_cnt,0)::bigint + COALESCE(comments_cnt,0)::bigint AS cnt
                FROM mv_monthly_trend
                WHERE month_start >= date_trunc('month', now()) - (interval '1 month' * :months)
                ORDER BY month_start
                """
            )
            rows = await session.execute(sql, {"months": months})
            series = [{"month": row.month_key, "count": int(row.cnt or 0)} for row in rows.fetchall()]
            trend = _compute_trend_labels_from_counts(series)
            # 若 runtime 失败，降级为 MV，视为 degraded
            return trend, "mv_monthly_trend", months * 30, True
        except Exception as fallback_exc:  # pragma: no cover
            print(f"❌ Trend fallback failed (mv_error={mv_error}): {fallback_exc}")
            return [], "trend_failed", months * 30, True
    # prefer_mv 且 MV 失败但 runtime 成功的情况：视为降级
    if prefer_mv and mv_error is not None:
        return trend, "runtime_topic_filtered", months * 30, True


def _analyze_price_signals(texts: list[str]) -> dict[str, Any]:
    if not texts:
        return {"sensitivity": "Unknown", "price_points": [], "keywords": {}}
    
    # 升级版正则：
    # 1. 排除年份 (1990-2030)
    # 2. 排除 "Model", "Series", "Ver", "No." 前缀的数字 (Lookbehind模拟)
    # 3. 匹配 $100, 100usd, 100 dollars
    
    # 预处理：先把 "Model 500" 这种干扰项替换掉，避免正则太复杂
    cleaned_texts = []
    noise_pattern = re.compile(r"(?:model|series|version|ver\.?|no\.?|part|gen|generation)\s*#?\s*\d+", re.IGNORECASE)
    year_pattern = re.compile(r"\b(?:19|20)\d{2}\b")
    
    for t in texts:
        if not t: continue
        # 替换掉干扰项为 "NOISE"
        no_noise = noise_pattern.sub("NOISE", t)
        # 替换掉年份
        no_year = year_pattern.sub("YEAR", no_noise)
        cleaned_texts.append(no_year)

    price_pattern = re.compile(r"(?:[$€£]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:usd|dollars|bucks)\b)", re.IGNORECASE)
    price_counts: Counter[str] = Counter()
    keyword_list = ["expensive", "cheap", "budget", "overpriced", "worth it", "investment", "pricey", "affordable"]
    keyword_counts: dict[str, int] = {k: 0 for k in keyword_list}

    for lower in [t.lower() for t in cleaned_texts]:
        for raw in price_pattern.findall(lower):
            # 清洗 "$ 500" -> "$500"
            normalized = raw.replace(" ", "").strip()
            # 统一 "$500usd" -> "$500"
            if "usd" in normalized: normalized = f"${normalized.replace('usd','').replace('dollars','').replace('bucks','')}"
            if not normalized.startswith(("$", "€", "£")):
                # 处理 "500 dollars"
                val = re.search(r"\d+", normalized)
                if val: normalized = f"${val.group(0)}"
            
            # 二次校验：排除太小的数字（如 $1, $2 可能是打赏或比喻）和太大的数字（异常值）
            try:
                val_num = float(re.sub(r"[^0-9.]", "", normalized))
                if 5 <= val_num <= 10000: # 假设我们关注正常消费品价格区间
                    price_counts[normalized] += 1
            except:
                pass

        for kw in keyword_list:
             keyword_counts[kw] += len(re.findall(rf"\b{kw}\b", lower))

    cheap_score = keyword_counts.get("cheap", 0) + keyword_counts.get("budget", 0) + keyword_counts.get("affordable", 0)
    quality_score = keyword_counts.get("expensive", 0) + keyword_counts.get("investment", 0) + keyword_counts.get("pricey", 0) + keyword_counts.get("overpriced", 0)
    
    if cheap_score > quality_score * 1.5:
        sensitivity = "High (Budget Focus)"
    elif quality_score > cheap_score * 1.5:
        sensitivity = "Low (Quality Focus)"
    elif cheap_score == 0 and quality_score == 0:
        sensitivity = "Unknown"
    else:
        sensitivity = "Medium (Balanced)"

    price_points = [p for p, _ in price_counts.most_common(5)] # 取前5个更稳
    keyword_counts = {k: v for k, v in keyword_counts.items() if v > 0}
    return {
        "sensitivity": sensitivity,
        "price_points": price_points,
        "keywords": keyword_counts,
    }


def _analyze_usage_context(texts: list[str], topic: str) -> dict[str, Any]:
    if not texts:
        return {"scenarios": [], "user_level": "Unknown"}
    scenario_map = {
        "home": "home",
        "house": "home",
        "kitchen": "kitchen",
        "office": "office",
        "work": "office",
        "job": "office",
        "travel": "travel",
        "trip": "travel",
        "commute": "travel",
        "car": "car",
        "vehicle": "car",
        "gym": "gym",
        "fitness": "gym",
        "bedroom": "bedroom",
        "bed": "bedroom",
    }
    purpose_map = {
        "gift": "gift",
        "present": "gift",
        "daily": "daily",
        "everyday": "daily",
        "professional": "professional",
        "pro": "professional",
        "beginner": "beginner",
        "starter": "beginner",
        "novice": "beginner",
    }
    scenario_counter: Counter[str] = Counter()
    purpose_counter: Counter[str] = Counter()

    for txt in texts:
        if not txt:
            continue
        lower = txt.lower()
        if "home office" in lower:
            scenario_counter["home office"] += 1
        tokens = re.findall(r"[a-zA-Z]+", lower)
        for token in tokens:
            if token in scenario_map:
                scenario_counter[scenario_map[token]] += 1
            if token in purpose_map:
                purpose_counter[purpose_map[token]] += 1

    scenarios = [{"name": name, "count": cnt} for name, cnt in scenario_counter.most_common(8) if cnt > 0]
    user_level = "Unknown"
    if purpose_counter:
        user_level = purpose_counter.most_common(1)[0][0]
    return {"scenarios": scenarios, "user_level": user_level}


def _load_dedup_threshold(config_path: Path) -> float:
    default = 0.85
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        value = payload.get("minhash_threshold", default)
        return float(value)
    except Exception:
        return default


def _print_config_summary(
    blacklist_config: BlacklistConfig,
    dedup_threshold: float,
    scoring_loader: ScoringRulesLoader,
) -> None:
    rules = scoring_loader.load()
    print(
        "⚙️ Config -> "
        f"blacklist:{len(blacklist_config.blacklisted_communities)} "
        f"downrank:{len(blacklist_config.downranked_communities)} "
        f"filter_keywords:{len(blacklist_config.filter_keywords)} | "
        f"dedup_threshold:{dedup_threshold} | "
        f"scoring_rules:+{len(rules.positive_keywords)} / -{len(rules.negative_keywords)} "
        f"negation:{len(rules.negation_patterns)}"
    )


def _compute_intent_scores(
    sample_comments: list[dict[str, str]],
    top_posts: list[dict[str, Any]],
    scorer: OpportunityScorer,
) -> tuple[dict[str, float], float]:
    if not sample_comments and not top_posts:
        return {}, 0.0

    intent_map: defaultdict[str, list[float]] = defaultdict(list)

    for comment in sample_comments:
        sub = _normalize_subreddit(comment.get("subreddit", ""))
        body = comment.get("body") or comment.get("text") or ""
        if not sub or not body:
            continue
        score = scorer.score(body).base_score
        intent_map[sub].append(score)

    for post in top_posts:
        sub = _normalize_subreddit(post.get("subreddit", ""))
        title = post.get("title") or post.get("text") or ""
        if not sub or not title:
            continue
        score = scorer.score(title).base_score
        intent_map[sub].append(score)

    averages: dict[str, float] = {}
    all_scores: list[float] = []
    for sub, values in intent_map.items():
        if not values:
            continue
        avg = sum(values) / len(values)
        averages[sub] = round(avg, 4)
        all_scores.extend(values)

    global_avg = round(sum(all_scores) / len(all_scores), 4) if all_scores else 0.0
    return averages, global_avg


def _top_brand_sentiment(entity_sentiment: dict[str, dict[str, float]], top_n: int = 5) -> list[dict[str, Any]]:
    if not entity_sentiment:
        return []
    scored: list[dict[str, Any]] = []
    for brand, aspects in entity_sentiment.items():
        vals = [v for v in aspects.values() if v is not None]
        if not vals:
            continue
        avg = sum(vals) / len(vals)
        scored.append({"brand": brand, "avg_sentiment": round(avg, 3), "support": len(vals)})
    scored.sort(key=lambda x: x["avg_sentiment"], reverse=True)
    return scored[:top_n]


def _apply_opportunity_scores(
    communities: list[dict[str, Any]],
    intent_scores: dict[str, float],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    updated: list[dict[str, Any]] = []
    final_scores: list[dict[str, Any]] = []
    max_rel = max((float(c.get("relevance_count", 0) or 0) for c in communities), default=1.0)
    for comm in communities:
        name = comm.get("name", "") or ""
        relevance = float(comm.get("relevance_count", 0.0) or 0.0)
        rel_norm = (relevance / max_rel) if max_rel else 0.0
        intent = float(
            intent_scores.get(_normalize_subreddit(name))
            or intent_scores.get(name.lower())
            or 0.0
        )
        final_score = round((rel_norm * 0.3) + (intent * 0.7), 4)
        enriched = {
            **comm,
            "intent_score": round(intent, 4),
            "relevance_norm": round(rel_norm, 4),
            "final_score": final_score,
        }
        updated.append(enriched)
        final_scores.append(
            {
                "community": name,
                "intent_score": round(intent, 4),
                "relevance": relevance,
                "final_score": final_score,
            }
        )
    return updated, final_scores


def _tokenize_topic(text: str) -> set[str]:
    tokens = re.split(r"[^A-Za-z0-9\u4e00-\u9fff]+", text.lower())
    return {t for t in tokens if t}


async def _expand_topic_semantically(
    topic: str, 
    model: str, 
    blacklist_config: BlacklistConfig
) -> Tuple[set[str], set[str], str]:
    """
    Uses LLM to expand the input topic (potentially Chinese) into relevant English keywords
    for Reddit community matching.
    """
    print(f"🧠 Expanding topic semantically: '{topic}'...")
    client = OpenAIChatClient(model=model)
    prompt = [
        {
            "role": "system",
            "content": (
                "You are a semantic mapping engine for Reddit analysis. "
                "Your goal is to translate and expand the user's input topic (which might be in Chinese) "
                "into a list of 5-10 HIGHLY SPECIFIC English keywords, Bigrams, or Subreddit names.\n"
                "CRITICAL RULES:\n"
                "1. NO generic single words (e.g., forbid 'machine', 'home', 'store', 'best', 'review').\n"
                "2. PREFER Bigrams (e.g., 'espresso machine', 'burr grinder', 'latte art') over broad terms.\n"
                "3. For 'Cross-border E-commerce', specific terms like 'AmazonFBA', 'Dropshipping' are okay.\n"
                "4. Identify 3-5 'Negative Keywords' (e.g., for 'Apple', exclude 'fruit', 'pie').\n"
                "5. Classify the topic into ONE vertical: [home_kitchen, outdoor_garden, baby_parenting, pets, consumer_electronics, fashion, beauty_health, automotive, finance_payments, software_services, gift_ideas, other].\n"
                "Return ONLY JSON: {\"keywords\": [...], \"exclude\": [...], \"vertical\": \"...\"}. No markdown."
            ),
        },
        {
            "role": "user",
            "content": f"Input Topic: {topic}\nOutput JSON object:",
        },
    ]
    
    try:
        response = await client.generate(prompt, max_tokens=200, temperature=0.3)
        # Clean up potential markdown code blocks
        cleaned = re.sub(r"```json|```", "", response).strip()
        payload = json.loads(cleaned)
        kws_list = []
        exclude_list = []
        vertical = "other"
        if isinstance(payload, dict):
            kws_list = payload.get("keywords") or payload.get("include") or []
            exclude_list = payload.get("exclude") or payload.get("negative") or []
            vertical = payload.get("vertical") or "other"
        elif isinstance(payload, list):
            kws_list = payload

        # Load Stopwords from Config (Config-Driven)
        stop_words = blacklist_config.semantic_expansion_stopwords
        if not stop_words:
            # Fallback safe defaults if config empty
            stop_words = {
                "machine", "home", "best", "review", "reviews", "reddit", "r", "advice", "help", 
                "store", "shop", "buy", "sell", "online", "question", "discussion", "comment",
                "com", "www", "http", "https"
            }

        expanded = set()
        for k in kws_list:
            if isinstance(k, str):
                # Actually, let's trust the tokenizer but filter the RESULTING tokens.
                tokens = _tokenize_topic(k)
                for t in tokens:
                    if t not in stop_words and len(t) > 2:
                        expanded.add(t)

        exclude_tokens = set()
        for e in exclude_list:
            if isinstance(e, str):
                tokens = _tokenize_topic(e)
                exclude_tokens.update(tokens)

        # Hard override: flashlight/EDC 关键词命中时优先归类 edc/consumer_electronics，避免落到 outdoor
        edc_cfg = _get_vertical_cfg("edc")
        edc_keywords = set(edc_cfg.get("keywords", [])) or {"flashlight", "flashlights", "edc", "olight", "lumen", "lumens", "tactical", "beam", "throw"}
        if any(kw in expanded for kw in edc_keywords):
            if vertical not in {"edc", "consumer_electronics"}:
                vertical = "edc"

        print(f"   -> Mapped to: {expanded}, exclude: {exclude_tokens}, vertical: {vertical}")
        return expanded, exclude_tokens, str(vertical or "other")
    except Exception as e:
        print(f"⚠️ Semantic expansion failed: {e}. Falling back to simple tokenization.")
    
    # Fallback: just tokenize the original input
    tokens = _tokenize_topic(topic)
    return tokens, set(), "other"


async def _fetch_top_brands_from_llm(topic: str, model: str, top_k: int = 20) -> list[str]:
    """LLM 动态品牌补全，返回品牌列表（去重、小写）。"""
    if not settings.openai_api_key:
        return []
    client = OpenAIChatClient(model=model)
    prompt = [
        {
            "role": "system",
            "content": (
                "You are a brand discovery assistant. Return only a JSON array of brand names "
                "for the given market/topic. No commentary, no markdown."
            ),
        },
        {
            "role": "user",
            "content": f"List top {top_k} brands for the topic: {topic}. Return JSON array only.",
        },
    ]
    try:
        resp = await client.generate(prompt, max_tokens=150, temperature=0.3)
        data = json.loads(resp)
        if isinstance(data, list):
            return list({str(x).strip().lower() for x in data if str(x).strip()})
    except Exception as exc:
        print(f"⚠️ LLM brand fetch failed: {exc}")
        return []
    return []


async def _backfill_brand_mentions(session, brands: list[str]) -> list[dict[str, Any]]:
    """基于 DB 计数品牌声量（标题+正文 ILIKE），只读查询。"""
    if not brands:
        return []
    results: list[dict[str, Any]] = []
    for b in brands:
        if not b:
            continue
        pattern = f"%{b}%"
        row = await session.execute(
            text(
                """
                SELECT COUNT(*) AS mentions
                FROM posts_raw
                WHERE is_current = true
                  AND (title ILIKE :pat OR body ILIKE :pat)
                """
            ),
            {"pat": pattern},
        )
        count = row.scalar() or 0
        results.append({"name": b, "mentions": int(count)})
    return results


async def _select_relevant_communities(
    session,
    stats: Any,
    topic_tokens: set[str],
    exclusion_tokens: set[str],
    relevance_map: dict[str, int],
    blacklist_config: BlacklistConfig,
    limit: int = 12,
    allowed_communities: list[str] | None = None,
) -> list[dict[str, Any]]:
    communities = getattr(stats, "community_stats", []) or []
    print(f"DEBUG: Total communities in stats: {len(communities)}")
    
    allowed_set = {s.lower() for s in (allowed_communities or [])}
    
    relevance_filtered = []
    for c in communities:
        name = (getattr(c, "subreddit", "") or "").lower()
        if not name:
            continue
            
        is_allowed = name in allowed_set or name.removeprefix("r/") in allowed_set
        
        # 1. Blacklist check (Bypass if is_allowed)
        if not is_allowed and blacklist_config.is_community_blacklisted(name):
            print(f"🚫 Blocked blacklisted community: r/{name.removeprefix('r/')}")
            continue
            
        # 2. Exclusion check (Bypass if is_allowed)
        if not is_allowed and any(ex in name for ex in exclusion_tokens):
            continue
            
        alt = name.removeprefix("r/")
        rel_cnt = relevance_map.get(name) or relevance_map.get(alt) or 0
        
        # 3. Priority Boost for Allowed Communities
        if is_allowed:
            # Force inclusion by giving it a high relevance count even if 0
            rel_cnt = max(rel_cnt, 10000)
            
        if rel_cnt <= 0:
            continue
        relevance_filtered.append((rel_cnt, c))

    if not relevance_filtered:
        print("WARN: No communities passed content relevance filter; falling back to original logic.")
        return [
            {
                "name": getattr(c, "subreddit", ""),
                "posts": getattr(c, "posts", 0),
                "comments": getattr(c, "comments", 0),
                "ps_ratio": getattr(c, "ps_ratio", None),
            }
            for c in (communities[:limit] if communities else [])
        ]

    relevance_filtered.sort(key=lambda x: x[0], reverse=True)

    candidate_names = [getattr(entry[1], "subreddit", "") for entry in relevance_filtered]
    
    # Pass topic_tokens to ranker for Name Relevance scoring
    ranking_scores = await compute_ranking_scores(
        session, 
        candidate_names, 
        relevance_map=relevance_map,
        topic_tokens=topic_tokens 
    ) if candidate_names else {}
    
    # Calculate Max Relevance for Normalization
    max_rel = max((r[0] for r in relevance_filtered), default=1)
    
    ranked = []
    for rel_cnt, c in relevance_filtered:
        name = getattr(c, "subreddit", "") or ""
        rank_score = float(ranking_scores.get(name.lower(), 0.0))
        
        # We rely heavily on the rank_score now as it handles density/name-matching
        # Keeping rel_norm as a backup volume signal
        rel_norm = rel_cnt / max_rel
        final_score = (rel_norm * 0.3) + (rank_score * 0.7)
        
        ranked.append((final_score, rel_cnt, c, rank_score))

    # Sort by Final Score DESC
    ranked.sort(key=lambda x: x[0], reverse=True)
    
    top = ranked[:limit]
    return [
        {
            "name": getattr(entry[2], "subreddit", ""),
            "posts": getattr(entry[2], "posts", 0),
            "comments": getattr(entry[2], "comments", 0),
            "ps_ratio": getattr(entry[2], "ps_ratio", None),
            "relevance_count": entry[1],
            "ranking_score": round(entry[3], 4),
            "final_score": round(entry[0], 4)
        }
        for entry in top
    ]


def _pick_relevant_subreddits(relevance_map: dict[str, int], limit: int = 120) -> list[str]:
    """Normalize and limit subreddits for downstream stats computation."""
    if not relevance_map:
        return []
    ordered = sorted(relevance_map.items(), key=lambda x: x[1], reverse=True)
    picked: list[str] = []
    seen: set[str] = set()
    for name, _ in ordered:
        norm = (name or "").strip().lower()
        if not norm:
            continue
        if not norm.startswith("r/"):
            norm = f"r/{norm}"
        if norm in seen:
            continue
        picked.append(norm)
        seen.add(norm)
        if len(picked) >= limit:
            break
    return picked


async def _fetch_need_distribution(
    session, subs: list[str], days: int = 365
) -> dict[str, dict[str, float]]:
    """Phase 5.2: Fetch L1 category distribution per community from post_scores.tags_analysis (V1)."""
    if not subs:
        return {}
    
    subs_clean = [s.lower() if s.lower().startswith("r/") else f"r/{s.lower()}" for s in subs if s]
    
    # New Logic: Parse JSONB tags_analysis->>'content_type'
    sql = text("""
        SELECT 
            lower(pr.subreddit) as subreddit,
            ps.tags_analysis->>'content_type' as raw_type,
            COUNT(*) as cnt
        FROM posts_raw pr
        JOIN post_scores_latest_v ps ON ps.post_id = pr.id
        WHERE lower(pr.subreddit) = ANY(:subs)
          AND pr.created_at >= NOW() - (interval '1 day' * :days)
        GROUP BY lower(pr.subreddit), raw_type
    """)
    
    try:
        result = await session.execute(sql, {"subs": subs_clean, "days": days})
        rows = result.fetchall()
    except Exception as e:
        print(f"⚠️ Need Dist Error: {e}")
        return {}
    
    totals: dict[str, int] = {}
    counts: dict[str, dict[str, int]] = {}
    
    # Mapping V1 content_type to Report Categories
    TYPE_MAP = {
        "ask_question": "Question",
        "user_review": "Review",
        "rant": "Complaint",
        "news_sharing": "News",
        "discussion": "Discussion",
        "other": "Other",
        None: "Other"
    }

    for row in rows:
        sub = row.subreddit
        raw_type = row.raw_type
        cat = TYPE_MAP.get(raw_type, "Other")
        cnt = row.cnt
        
        totals[sub] = totals.get(sub, 0) + cnt
        if sub not in counts:
            counts[sub] = {}
        counts[sub][cat] = counts[sub].get(cat, 0) + cnt
    
    distribution: dict[str, dict[str, float]] = {}
    for sub, cats in counts.items():
        total = totals.get(sub, 1)
        distribution[sub] = {
            cat: round(cnt / total * 100, 1) 
            for cat, cnt in cats.items()
        }
    
    print(f"📊 Phase 5.2: Need distribution loaded for {len(distribution)} communities (V1 Source)")
    return distribution


async def _score_communities_contextually(
    session,
    subs: list[str],
    topic_tokens: set[str],
    vertical: str,
    days: int,
    limit: int = 120,
) -> dict[str, dict[str, float]]:
    """Compute topic/off-topic hit counts and semantic scores for communities to drive dynamic allow/block."""
    if not subs or not topic_tokens:
        return {}
    subs = [s.lower() if s.lower().startswith("r/") else f"r/{s.lower()}" for s in subs][:limit]
    topic_query = " | ".join(t for t in topic_tokens if t)
    off_tokens = VERTICAL_OFFTOPIC.get(vertical or "", set())
    off_query = " | ".join(off_tokens) if off_tokens else ""
    has_off = bool(off_query)

    async def _count(sql: str, params: dict[str, Any]) -> dict[str, int]:
        res: Result = await session.execute(text(sql), params)
        out: dict[str, int] = {}
        for row in res.fetchall():
            sr = getattr(row, "sr", None)
            cnt = getattr(row, "cnt", 0) or 0
            if sr:
                out[sr] = int(cnt)
        return out

    # ---- Semantic signals (preferred) ----
    # topic embedding
    topic_embed = None
    try:
        topic_embed = embedding_service.encode(" ".join(topic_tokens))
    except Exception:
        topic_embed = None

    def _embed_to_str(vec: Any) -> str:
        try:
            return str(vec)
        except Exception:
            return ""

    topic_counts: dict[str, int] = {}
    off_counts: dict[str, int] = {}
    sim_scores: dict[str, float] = {}

    if topic_embed is not None:
        topic_embed_str = _embed_to_str(topic_embed)
        sql_sem_topic = """
            SELECT lower(p.subreddit) AS sr, COUNT(*) AS cnt
            FROM posts_raw p
            JOIN post_embeddings pe ON pe.post_id = p.id
            WHERE lower(p.subreddit) = ANY(:subs)
              AND p.created_at >= NOW() - (interval '1 day' * :days)
              AND pe.embedding <=> :emb < :threshold
            GROUP BY sr
        """
        topic_counts = await _count(sql_sem_topic, {
            "subs": subs, "days": days, "emb": topic_embed_str, "threshold": SEMANTIC_SIM_THRESHOLD
        })
        # Approximate similarity by hit count; used for sorting
        sim_scores = {k: v for k, v in topic_counts.items()}

    if has_off and topic_embed is not None:
        try:
            off_embed = embedding_service.encode(off_query)
            off_embed_str = _embed_to_str(off_embed)
            sql_sem_off = """
                SELECT lower(p.subreddit) AS sr, COUNT(*) AS cnt
                FROM posts_raw p
                JOIN post_embeddings pe ON pe.post_id = p.id
                WHERE lower(p.subreddit) = ANY(:subs)
                  AND p.created_at >= NOW() - (interval '1 day' * :days)
                  AND pe.embedding <=> :emb < :threshold
                GROUP BY sr
            """
            off_counts = await _count(sql_sem_off, {
                "subs": subs, "days": days, "emb": off_embed_str, "threshold": SEMANTIC_SIM_THRESHOLD
            })
        except Exception:
            off_counts = {}

    # Fallback to lexical if embedding failed
    if topic_embed is None:
        sql_topic = """
            SELECT lower(subreddit) AS sr, COUNT(*) AS cnt
            FROM comments
            WHERE lower(subreddit) = ANY(:subs)
              AND created_utc >= NOW() - (interval '1 day' * :days)
              AND to_tsvector('english', COALESCE(body, '')) @@ to_tsquery('english', :q)
            GROUP BY sr
        """
        topic_counts = await _count(sql_topic, {"subs": subs, "days": days, "q": topic_query})
    if has_off and topic_embed is None:
        sql_off = """
            SELECT lower(subreddit) AS sr, COUNT(*) AS cnt
            FROM comments
            WHERE lower(subreddit) = ANY(:subs)
              AND created_utc >= NOW() - (interval '1 day' * :days)
              AND to_tsvector('english', COALESCE(body, '')) @@ to_tsquery('english', :q)
            GROUP BY sr
        """
        off_counts = await _count(sql_off, {"subs": subs, "days": days, "q": off_query or "''"})

    out: dict[str, dict[str, float]] = {}
    for sub in subs:
        t = topic_counts.get(sub, 0)
        o = off_counts.get(sub, 0)
        total = t + o if (t + o) > 0 else max(t, o)
        off_ratio = (o / total) if total else 0.0
        out[sub] = {
            "topic_hits": float(t),
            "off_hits": float(o),
            "off_ratio": off_ratio,
            "sim_score": float(sim_scores.get(sub, t)),
        }
    return out


def _build_facts(
    stats: Any,
    clusters: Iterable[Any],
    topic: str,
    topic_tokens: set[str],
    days: int,
    selected_communities: Optional[list[dict[str, Any]]] = None,
    need_distribution: Optional[dict[str, dict[str, float]]] = None,  # Phase 5.2
    brand_backfill: Optional[list[dict[str, Any]]] = None,
    market_landscape: Optional[dict[str, Any]] = None,
    pain_tree: Optional[list[dict[str, Any]]] = None,
    topic_keywords_override: Optional[list[str]] = None,
    business_signals: Optional[dict[str, Any]] = None,
    market_saturation: Optional[list[dict[str, Any]]] = None,
    extracted_keywords: Optional[list[str]] = None,
    ranked_communities: Optional[list[dict[str, Any]]] = None,
    price_analysis: Optional[dict[str, Any]] = None,
    usage_context: Optional[dict[str, Any]] = None,
    community_personas: Optional[list[dict[str, Any]]] = None,
) -> str:
    """把数值事实打包给 LLM，避免编造。Phase 5.2: 新增 need_distribution (需求图谱透视)。"""
    top_comm = selected_communities or []
    ps = getattr(stats, "global_ps_ratio", None)
    total_posts = sum(getattr(c, "posts", 0) for c in getattr(stats, "community_stats", []) or [])
    total_comments = sum(getattr(c, "comments", 0) for c in getattr(stats, "community_stats", []) or [])
    aspects = [
        {
            "aspect": getattr(a, "aspect", ""),
            "pain": getattr(a, "pain", 0),
            "total": getattr(a, "total", 0),
            "pain_ratio": getattr(a, "pain_ratio", None),
        }
        for a in getattr(stats, "aspect_breakdown", []) or []
    ]
    market_landscape = market_landscape or {}
    # 品牌共现原始列表（用于 brand_pain 字段）
    brand_co_raw = [
        {
            "brand": getattr(b, "brand", ""),
            "mentions": getattr(b, "mentions", 0),
            "aspects": getattr(b, "aspects", []),
        }
        for b in getattr(stats, "brand_pain_cooccurrence", []) or []
    ]
    
    # Apply layering to filter out platforms/logistics from brand_pain
    brand_co_layered = assign_competitor_layers([{"name": b["brand"]} for b in brand_co_raw])
    brand_layer_map = {item["name"]: item["layer"] for item in brand_co_layered}
    
    FILTER_LAYERS = {"platforms", "logistics", "channels", "attributes", "noise"}
    brand_co = [
        b for b in brand_co_raw
        if brand_layer_map.get(b["brand"], "brands") not in FILTER_LAYERS
    ]
    if not market_landscape:
        platform_map: dict[str, int] = {}
        channel_map: dict[str, int] = {}
        brand_map: dict[str, int] = {}

        def _accumulate(target: dict[str, int], name: str, cnt: int) -> None:
            if not name:
                return
            target[name] = target.get(name, 0) + int(cnt)

        # market_landscape 需要保留平台/渠道等全景；brand_pain 则需要过滤掉这些“非品牌”项。
        for entry in brand_co_raw + (brand_backfill or []):
            if isinstance(entry, dict):
                name = entry.get("brand") or entry.get("name")
                mentions = entry.get("mentions", 0)
            else:
                name = getattr(entry, "brand", None)
                mentions = getattr(entry, "mentions", 0)
            cls = _classify_entity(name or "")
            if cls == "platform":
                _accumulate(platform_map, name, mentions or 0)
            elif cls == "channel":
                _accumulate(channel_map, name, mentions or 0)
            elif cls == "potential_brand":
                _accumulate(brand_map, name, mentions or 0)

        market_landscape = {
            "platforms": [{"name": n, "mentions": m} for n, m in platform_map.items() if m > 0],
            "channels": [{"name": n, "mentions": m} for n, m in channel_map.items() if m > 0],
            "brands": [{"name": n, "mentions": m} for n, m in brand_map.items() if m > 0],
        }

    # 可选：痛点词典键（用于提示 LLM 主题相关词汇，避免跑题）
    pain_dict_keys: list[str] = []
    pain_path = Path("backend/config/pain_dictionary.yaml")
    if pain_path.exists():
        try:
            data = yaml.safe_load(pain_path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                all_keys = list(data.keys())
                # 仅保留与 topic token 相关的词条，避免跑偏；若没有匹配则取前 50 条兜底
                # tokens = _tokenize_topic(topic)  <-- REMOVED
                filtered = [k for k in all_keys if any(t in k.lower() for t in topic_tokens)]
                pain_dict_keys = (filtered or all_keys)[:50]
        except Exception:
            pain_dict_keys = []

    cluster_keywords: list[str] = []
    sample_comments: list[str] = []
    for c in clusters:
        if isinstance(c, dict):
            cluster_keywords.extend(c.get("keywords", []) or [])
            sample_comments.extend((c.get("samples", []) or [])[:2])
        else:
            cluster_keywords.extend(getattr(c, "top_keywords", []) or [])
            sample_comments.extend((getattr(c, "sample_comments", []) or [])[:2])
    # 主题关键词池：外部提取优先，其次词典/聚类/aspect
    topic_keywords = topic_keywords_override or list(
        {
            *pain_dict_keys,
            *cluster_keywords,
            *[a.get("aspect") for a in aspects if a.get("aspect")],
        }
    )
    topic_keywords = [k for k in topic_keywords if k]
    topic_keywords = list({*topic_keywords, *topic_tokens})[:50]
    # 简易机会评分
    opportunity_scores = []
    saturation_inv = 0.0
    if ps is not None:
        saturation_inv = max(0.0, 1 - min(ps, 2.0) / 2.0)
    for comm in top_comm:
        pd = float(comm.get("pain_density", 0.0) or 0.0)
        gr = float(comm.get("growth_rate", 0.0) or 0.0)
        score = (pd * 40) + (gr * 30) + (saturation_inv * 30)
        opportunity_scores.append(
            {
                "community": comm.get("name"),
                "pain_density": pd,
                "growth_rate": gr,
                "saturation_inverse": saturation_inv,
                "score": round(score, 2),
            }
        )

    facts = {
        "topic": topic,
        "time_window_days": days,
        "since_utc": getattr(stats, "since_utc", ""),
        "global_ps_ratio": ps,
        "total_posts": total_posts,
        "total_comments": total_comments,
        "communities": ranked_communities or top_comm,
        "pain_dictionary_keys": pain_dict_keys,
        "topic_keywords": topic_keywords,
        "extracted_keywords": extracted_keywords or [],
        "market_saturation": market_saturation or [],
        "market_landscape": market_landscape,
        "opportunity_scores": opportunity_scores,
        "business_signals": business_signals or {},
        "pain_clusters": pain_tree or [
            {
                "topic": (c.get("topic") if isinstance(c, dict) else getattr(c, "topic", "")),
                "total_frequency": (c.get("total_frequency") if isinstance(c, dict) else getattr(c, "size", 0)),
                "samples": (c.get("samples") if isinstance(c, dict) else getattr(c, "sample_comments", [])),
                "top_communities": (c.get("top_communities") if isinstance(c, dict) else getattr(c, "aspects", [])),
                "negative_mean": (c.get("negative_mean") if isinstance(c, dict) else None),
            }
            for c in clusters
        ],
        "aspect_breakdown": aspects[:6],  # top aspects
        "brand_pain": brand_co[:10],  # top brand/pain cooccurrence
        "sample_comments": sample_comments[:10],
        "sample_comments_db": [],  # placeholder,填充于 main
        "need_distribution": need_distribution or {},  # Phase 5.2: 需求图谱透视
        "pain_tree": pain_tree or [],
        "price_analysis": price_analysis or {},
        "usage_context": usage_context or {},
        "community_personas": community_personas or [],
    }
    return json.dumps(facts, ensure_ascii=False, indent=2)


def _make_prompt_part1(topic: str, product_desc: str, facts: str) -> list[dict[str, str]]:
    """
    Stage 1 Prompt: Modules 1-4 (Top Info -> Core Battlefields).
    V7: Full prompts.md version with detailed field explanations.
    """
    user = f'''【分析任务】
product_desc: {product_desc}

这次的事实数据 facts，已经按照 T1 社区和当前赛道汇总好，结构大致包括：
- overall: 讨论总量、时间趋势、整体 P/S Ratio
- audience_mix: 不同人群类型（吐槽/避坑党、找货/工具党、进阶/学习党）的占比
- topic_trends: 主要话题/场景的热度变化
- community_stats: 各核心社区的帖子/评论量、P/S Ratio、人群结构
- platform_brand_landscape: 购买渠道 / 品牌 / 信息来源三层格局
- business_signals: high_value_pains, buying_opportunities, competitor_insights, market_saturation 等
- sample_comments_db: 用于说明问题的代表性帖子和评论（含 URL）

【你的任务】
只根据给你的 facts 和 product_desc，生成“报告的第一部分（模块 1–4）”，用 Markdown 输出，严格按照下面结构：

1. 顶部信息
   - 标题：`{product_desc} · 市场洞察报告（T1 社区版）`
   - 简述：2–4 句，包含：
     - 这次你在看什么问题 / 什么赛道；
     - 主要参考了哪些 Reddit 社区（举 3–5 个核心社区名）；
     - 时间范围（例如“过去 12 个月的讨论”）；
     - 大致声量（用“讨论量 / 评论量”来形容，不提“用户数 / 销量 / 市场份额”）。

2. 决策卡片（4 小节，2–3 行一句话 + 2–3 条 bullet 说明即可）

2.1 需求趋势
- 用 1–2 句话总结：这个话题在过去一段时间是“爆发式增长 / 稳定存在 / 略有降温”。
- 后面列 2–3 条依据：
  - 哪些话题在变多或变少（引用 topic_trends）；
  - 如果 business_signals 或 market_saturation 标记了“EXPLODING”，要点出来。

2.2 需求图谱透视（人群结构）
- 用“吐槽/避坑党、找货/工具党、进阶/学习党”三类，描述不同人群的大致占比。
- 说明这种结构意味着什么（坑多？工具党多？学习党多？）。
- 用一句“性格总结”收尾，比如：“这是一个吐槽声很大、但大家又离不开的市场。”

2.3 P/S Ratio 大白话
- 用一句话给出大概的 P/S Ratio（例如“整体约为 1.3:1”）。
- 用 1–2 句人话解释：问题贴比解决贴多还是少，这代表现实中的“乱 / 可学套路 / 老玩家传帮带”。
- 落在用户身上：
  - 对普通卖家意味着什么（更需要小心试错 / 多抄作业）；
  - 对工具/服务方意味着什么（是否还有“问题比答案多”的空间）。

2.4 高潜力社群（3–5 个）
- 从 community_stats 里挑 3–5 个和当前主题最相关、声量大、信息质量高的社区。
- 每个按如下格式描述：
  - `r/xxx（P/S Ratio ≈ x.xx）`
  - 这里的人大致是什么类型（新手多 / 老玩家多 / 工具党多）；
  - 主要在聊哪些场景（选品 / 广告 / 平台规则 / 物流…）；
  - 最后告诉读者：“如果你是 XX 类型的人，这个社区适合你拿来做什么”。

3. 概览（市场健康度）

3.1 竞争格局（平台 / 品牌 / 信息渠道）
- 用三小段讲清楚：
  1）购买渠道：大家通常去哪些平台下单，用“讨论热度 / 默认购买渠道 / 比价备胎”来描述；
  2）品牌关注：经常被拿出来对比的 2–3 个品牌，以及它们各自常被提到的问题或场景；
  3）信息来源：大家去哪里看评测 / 教程 / 经验（YouTube/Google/Instagram/博客等），强调这些是“做功课的地方”，不是“卖货平台”。

3.2 P/S Ratio 深度解读
- 在前面 P/S 的基础上，再深一层解释：
  - 这是“坑很多但机会大”的阶段，还是“套路成熟、比的是细活”的阶段。
- 最后用一句话帮用户定位自己：
  - “你现在进来的，是一片坑多但机会也大的荒地，还是一条已经修好但有点挤的高速公路。”

4. 核心战场推荐（3–4 个社区画像）
- 从 community_stats 里挑 3–4 个“最值得长期蹲点”的社区。
- 每个社区用 3 点描述：
  1）战场标题：`战场 N：r/xxx（P/S Ratio ≈ x.xx）`
  2）人群画像：吐槽/避坑党多、找货/工具党多、还是进阶/学习党多；
  3）使用建议：
     - 来这里适合干什么（看别人踩坑 / 看别人选品 / 对比工具…）；
     - 怎么逛才高效（先搜旧帖 / 关注某类标题 / 关注哪类发帖人）。

【输出要求】
- 输出为一份完整的 Markdown 文本，只包含模块 1–4。
- 不要出现 JSON 字段名和内部变量名，只用自然语言表达。
- 不要凑字数，每一段都要基于 facts，有“凭啥这么说”的依据。

【数据事实】
{facts}'''
    return [{"role": "system", "content": REPORT_SYSTEM_PROMPT_V2}, {"role": "user", "content": user}]
    user = f"【分析任务】product_desc: {product_desc}\n\n【数据事实】\n{facts}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _make_prompt_part2(topic: str, product_desc: str, facts: str) -> list[dict[str, str]]:
    """
    Stage 2 Prompt: Modules 5-7 (User Pains -> Opportunities).
    V7: Full prompts.md version with detailed format requirements.
    """
    user = f'''【分析任务】
product_desc: {product_desc}

你将继续撰写同一份报告的第二部分（模块 5–7），facts 输入与 Part1 相同，包含：
- business_signals（high_value_pains / buying_opportunities / competitor_insights / market_saturation）
- pain_tree（从表层抱怨到根因的结构）
- sample_comments_db（附带 URL 的真实评论样本）
- 其他你需要的聚合指标

当前 output_part = "part2"：
你只负责“用户痛点 / 决策驱动力 / 商业机会”，不能重复写模块 1–4 的内容。

------------------------------------------------
【全局去重规则】

- 如果某个痛点已经在模块 2 或 3 里被点过（比如“物流波动大”），
  在模块 5–7 再提到时，只用一句话交代背景，重点放在：
  - 这背后真正的机制是什么；
  - 用户是怎么被影响的；
  - 你可以怎么选/怎么做。

- 模块 6（驱动力）和模块 7（机会）：
  - 不要为了格式凑够 3 条；
  - 如果有 2 条特别扎实，就只写 2 条。

------------------------------------------------
【你的任务】
基于 facts 和 sample_comments_db，生成模块 5–7，用 Markdown 输出：

5. 用户痛点（3 个）

- 从 business_signals.high_value_pains 里挑出 3 个“最值得写一整卡片”的痛点。
- 每个痛点写 5 块内容：

  1）痛点标题
     - 一句“用户口吻”的问题名，比如：“花了不少钱，效果却不稳”。

  2）用户之声（真实评论提炼）
     - 从 sample_comments_db 里选 1–3 条典型说法，保留口语感觉，注明大概社区名；
     - 不要直接复制一整段，适度压缩，但要有原话感。

  3）数据印象
     - 用“从痛点分布来看 / 在所有抱怨里占比挺高”这类说法，说明它不是个孤立个案；
     - 不提字段名，只说“在 Reddit 讨论里经常出现 / 在这类话题里特别常见”。

  4）解读（机制 / 损失 / 连锁反应）
     - 机制：结合 pain_tree，说清楚为什么会出现这个问题；
     - 损失：对卖家/用户会带来什么具体损失（时间、钱、信任…）；
     - 连锁反应：比如会导致“更换平台、换工具、暂停投放”等后续行为。

  5）链接（🔗 必须有）
     - 至少给出 1 条代表性的讨论链接（来自 sample_comments_db 的 URL），
       用“示例讨论：链接”这种形式挂在最后。

------------------------------------------------
6. Top 购买 / 决策驱动力（2–3 条）

- 重点不再是“哪儿有坑”，而是：
  “当用户真正要做选择时，脑子里最在意的那几件事是什么？”
- 从 buying_opportunities 和 business_signals 里挑出 2–3 条最强的驱动力。

每条写 3 部分：

1）标题
   - 抓住核心，例如：“别再踩坑：稳定比便宜更重要”。

2）展开说明
   - 用 2–3 句说清楚：
     - 用户是通过什么行为体现这一点的（频繁对比某个指标？不断问同一个问题？）；
     - 这和前面的痛点有什么关系（简短带一句就行）。

3）给用户的行动建议
   - 选平台 / 选工具 / 选服务时，该重点问哪些问题；
   - 哪些信号一旦看到，就说明“可能不适合你”；
   - 建议要尽量具体，比如：“多看历史负面贴 / 主动搜 ‘关键词 + scam/refund’ 过滤雷区”。

------------------------------------------------
7. 商业机会（2 张机会卡）

- 参考 business_signals.buying_opportunities 和 market_saturation，
  写 2 张“机会卡”，分别是：

  机会卡 1：信息透明 / 预测型机会
  机会卡 2：整合 / 降复杂度型机会

每张机会卡写 4 块内容：

1）对应痛点
   - 引用模块 5 中的某个痛点名，一句话带过背景。

2）目标人群 / 社区
   - 说明谁最需要这样的东西：
     - 比如“多平台兼顾的小卖家 / 预算紧张的小团队 / 新手卖家 / 工具党”。

3）产品定位（大白话）
   - 用一句话说清楚：
     - “它其实就是帮你在【某个具体场景】下，提前看清/算清/对比好【哪件事】的东西。”

4）卖点（双视角）
   - 对普通用户/卖家：
     - 用 2–3 个 bullet，说清楚选这类产品/服务时，最该看什么。
   - 对服务商/工具方：
     - 用 1–2 句点出：如果想在这条赛道站稳，最该把哪 1–2 件事做到极致。

【输出要求】
- 只输出模块 5–7 的内容，Markdown 格式。
- 所有痛点和机会，必须能在 business_signals 和 sample_comments_db 里找到对应证据；
- 不要凑数，写不满 3 条时，可以只写 2 条，但要扎实。

【数据事实】
{facts}'''
    return [{"role": "system", "content": REPORT_SYSTEM_PROMPT_V2}, {"role": "user", "content": user}]


def _make_prompt_part2_trimmed(topic: str, product_desc: str, facts: str) -> list[dict[str, str]]:
    """
    Tier B Prompt: Modules 5-6 only (trimmed, evidence-first, no forced filling).
    """
    user = f'''【分析任务】
product_desc: {product_desc}

你将撰写同一份报告的第二部分（精简版），只输出模块 5–6。
这次数据量/证据不足时，宁可少写，也不要胡写。

【你必须遵守的原则】
- 所有结论必须能在 facts 里找到依据（high_value_pains / sample_comments_db / market_saturation 等）。
- 不要凑满 3 条：写 0–2 条也可以，但要“对味”和“有证据”。
- 如果证据不足，用一句话明确说明“目前证据不足，暂不下结论”，不要编造。
- 这是“早期观察版”：模块标题里要明确写“样本仍在累积”，语气要克制，不要写成定论。

【输出结构】（只输出 5–6）

5. 用户痛点（早期观察｜样本仍在累积，0–2 个）
- 只从 business_signals.high_value_pains 里挑。
- 每个痛点包含：
  1）痛点标题（用户口吻，标题末尾加上“（早期观察）”）
  2）用户之声（1–2 条，来自 sample_comments_db，注明社区）
  3）数据印象（mentions/作者量的口头说法，不报字段名）
  4）解读（为什么会这样、会造成什么损失）
  5）链接（至少 1 条 URL）

6. Top 决策驱动力（早期观察｜样本仍在累积，0–2 条）
- 只写“卖家做选择时最在意什么”，不要写泛泛鸡汤。
- 每条包含：
  1）标题
  2）展开说明（2–3 句）
  3）行动建议（尽量具体）

【数据事实】
{facts}'''
    return [{"role": "system", "content": REPORT_SYSTEM_PROMPT_V2}, {"role": "user", "content": user}]


def _make_prompt_scouting_brief(topic: str, product_desc: str, facts: str) -> list[dict[str, str]]:
    """
    Tier C Prompt: Scouting brief, modules 1-3 only (no pains/opportunities conclusions).
    """
    user = f'''【分析任务】
product_desc: {product_desc}

你要写一份“勘探简报”，只输出模块 1–3（不写 4–7）。
这份简报的目标不是给结论，而是：告诉读者“现在讨论主要集中在哪些社区、热不热、谁在聊、聊的方向像不像我们要的赛道”。

【你必须遵守的原则】
- 只根据给你的 facts 写，不要编造不存在的数据或案例。
- 如果事实里没有足够证据支撑某个判断，就写“目前证据不足，先不下结论”。
- 语气要实话实说：这是早期观察雷达，不是完整版市场地图。

【输出结构】（只输出 1–3）

1. 顶部信息
- 标题：`{product_desc} · 勘探简报（T1 社区版）`
- 简述：2–4 句，说明：
  - 这次在看什么赛道；
  - 主要参考了哪些社区（3–5 个）；
  - 时间范围与讨论量级；
  - 一句“当前还处在勘探阶段”的提醒（不要用内部字段名）。

2. 决策卡片（3 小节即可）
2.1 需求趋势（热不热、涨不涨）
2.2 人群结构（吐槽/避坑党、找货/工具党、进阶/学习党）
2.3 P/S Ratio 大白话（问题贴 vs 解法贴）

3. 概览（市场健康度）
3.1 竞争格局（平台/品牌/信息渠道，能说多少说多少）
3.2 P/S Ratio 深度解读（一句话定性 + 一句建议）

【数据事实】
{facts}'''
    return [{"role": "system", "content": REPORT_SYSTEM_PROMPT_V2}, {"role": "user", "content": user}]


async def _llm_generate(prompt: list[dict[str, str]], model: str) -> str:
    # Phase 5.3: Increased timeout from default 8s to 60s for longer report generation
    client = OpenAIChatClient(model=model, timeout=60.0)
    return await client.generate(prompt, max_tokens=4000, temperature=0.25)


async def _fetch_top_posts(
    session,
    subs: list[str],
    keywords: list[str],
    days: int = 365,
    limit: int = 50,
    required_entities: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """
    Fetch high-value posts (scored by Phase D pipeline) for LLM context.
    Uses post_scores_latest_v (rulebook_v1, is_latest) to filter noise.
    """
    if not subs:
        return [], False
    subs = [s.lower() if s.lower().startswith("r/") else f"r/{s.lower()}" for s in subs if s]
    
    # Keyword filtering still useful for Topic Relevance within the high-value pool
    kw = [k for k in keywords[:5] if k]
    patterns = [f"%{k}%" for k in kw] if kw else []
    
    # Exclude patterns (must NOT match title or body)
    exclude_patterns = [f"%{k}%" for k in (exclude_keywords or []) if k]
    has_exclude = bool(exclude_patterns)
    
    # Required patterns (must match title or body) - Any match
    # 'required_entities' acts as "Must hit at least one of these if provided"
    req_patterns = [f"%{k}%" for k in (required_entities or []) if k]
    has_req = bool(req_patterns)
    
    rows_result: list[Any] = []
    fallback_used = False

    # Primary Strategy: V1 Scored Posts (Value >= 6.0)
    # This ensures we only feed "Business Relevant" posts to the LLM
    sql_v1 = text(
        """
        SELECT p.source_post_id, p.author_id, p.author_name, p.title, p.body, p.score, p.subreddit, p.url, p.created_at, ps.value_score
        FROM post_scores_latest_v ps
        JOIN posts_raw p ON ps.post_id = p.id
        WHERE ps.value_score >= 6.0
          AND lower(p.subreddit) = ANY(:subs)
          AND (:has_patterns = FALSE OR (lower(p.title) ILIKE ANY(:patterns) OR lower(COALESCE(p.body, '')) ILIKE ANY(:patterns)))
          AND (:has_exclude = FALSE OR NOT (lower(p.title) ILIKE ANY(:exclude_patterns) OR lower(p.body) ILIKE ANY(:exclude_patterns)))
          AND (:has_req = FALSE OR (lower(p.title) ILIKE ANY(:req_patterns) OR lower(p.body) ILIKE ANY(:req_patterns)))
          AND p.created_at > NOW() - (interval '1 day' * :days)
        ORDER BY ps.value_score DESC, p.score DESC
        LIMIT :limit
        """
    )
    
    try:
        res = await session.execute(sql_v1, {
            "subs": subs, 
            "patterns": patterns, 
            "has_patterns": bool(patterns),
            "exclude_patterns": exclude_patterns,
            "has_exclude": has_exclude,
            "req_patterns": req_patterns,
            "has_req": has_req,
            "limit": limit, 
            "days": days
        })
        rows_result = res.fetchall()
    except Exception as e:
        print(f"⚠️ V1 Fetch Error: {e}")
        rows_result = []

    # Fallback: If V1 yields nothing (maybe topic is too niche or not scored yet),
    # revert to raw Score-based fetch
    if len(rows_result) < 5:
        print("⚠️ Not enough V1 posts found, using legacy fallback.")
        fallback_used = True
        sql_fallback = text(
            """
            SELECT p.source_post_id, p.author_id, p.author_name, p.title, p.body, p.score, p.subreddit, p.url, p.created_at
            FROM posts_raw p
            WHERE lower(p.subreddit) = ANY(:subs)
              AND (:has_patterns = FALSE OR (lower(p.title) ILIKE ANY(:patterns) OR lower(COALESCE(p.body, '')) ILIKE ANY(:patterns)))
              AND (:has_exclude = FALSE OR NOT (lower(p.title) ILIKE ANY(:exclude_patterns) OR lower(p.body) ILIKE ANY(:exclude_patterns)))
              AND (:has_req = FALSE OR (lower(p.title) ILIKE ANY(:req_patterns) OR lower(p.body) ILIKE ANY(:req_patterns)))
              AND p.created_at > NOW() - (interval '1 day' * :days)
              AND p.score >= 5
            ORDER BY p.score DESC
            LIMIT :limit
            """
        )
        res = await session.execute(sql_fallback, {
            "subs": subs,
            "patterns": patterns,
            "has_patterns": bool(patterns),
            "exclude_patterns": exclude_patterns,
            "has_exclude": has_exclude,
            "req_patterns": req_patterns,
            "has_req": has_req,
            "limit": limit,
            "days": max(days, 540) # Wider window for fallback
        })
        rows_result = res.fetchall()

    out: list[dict[str, Any]] = []
    for r in rows_result:
        url = getattr(r, "url", None)
        # FORCE LINK INJECTION
        title_with_link = f"{r.title} [🔗]({url})" if url else r.title
        created_at = getattr(r, "created_at", None)
        out.append({
            "post_id": str(getattr(r, "source_post_id", "") or ""),
            "author_id": getattr(r, "author_id", None),
            "author_name": getattr(r, "author_name", None),
            "created_at": created_at.isoformat() if created_at else None,
            "title": title_with_link,
            "title_raw": getattr(r, "title", None),
            "body": getattr(r, "body", None),
            "score": getattr(r, "score", 0),
            "subreddit": getattr(r, "subreddit", ""),
            "url": url,
            "value_score": getattr(r, "value_score", 0) # Track value score if available
        })

    # Bucket Strategy: Limit per subreddit to ensure diversity
    bucketed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in out:
        sub = (item.get("subreddit") or "").lower()
        if len(bucketed[sub]) < 10:
            bucketed[sub].append(item)
    
    # Flatten and Sort by Value Score (if present) or Raw Score
    final_out = [it for items in bucketed.values() for it in items]
    final_out.sort(key=lambda x: (x.get("value_score") or 0, x.get("score") or 0), reverse=True)
    
    return final_out, fallback_used


async def _fetch_sample_comments(
    session,
    subs: list[str],
    keywords: list[str],
    days: int = 365,
    limit: int = 150,
    dedup_threshold: float | None = None,
    per_sub_comment_cap: int = 40,
    fallback_threshold_comments: int = 60,
    fallback_days: int = 540,
    use_fallback: bool = False,
    fallback_min_len_other: int | None = None,
    exclude_keywords: list[str] | None = None,
    required_entities: list[str] | None = None,
) -> list[dict[str, str]]:
    """按主题关键词抽取评论片段，优先从高分帖子(V1 Scored)中抓取。"""
    if not subs or not keywords:
        return []
    # Ensure subreddits have r/ prefix to match DB format
    subs = [s.lower() if s.lower().startswith("r/") else f"r/{s.lower()}" for s in subs if s]
    kw = keywords[:5]
    kw = [k for k in kw if k and len(k) > 2 and k.lower() not in {"pot", "pan", "maker", "cook", "kitchen"}]
    if not kw:
        kw = [k for k in keywords if k and len(k) > 3][:5]
    
    solution_kw = ["fixed", "solved", "solution", "tip", "trick", "method", "workaround"]
    all_patterns = [f"%{k}%" for k in (kw + solution_kw)]
    
    # Exclude patterns
    exclude_patterns = [f"%{k}%" for k in (exclude_keywords or []) if k]
    has_exclude = bool(exclude_patterns)

    # Required patterns (must match post OR comment) - Any match
    req_patterns = [f"%{k}%" for k in (required_entities or []) if k]
    has_req = bool(req_patterns)
    
    # New Logic: Join post_scores_latest_v to filter by Post Value >= 6
    sql = text(
        """
        SELECT c.id, c.author_id, c.author_name, c.body, c.subreddit, c.source_post_id, c.reddit_comment_id, c.permalink, c.created_utc, c.score
        FROM comments c
        JOIN posts_raw p ON c.post_id = p.id
        JOIN post_scores_latest_v ps ON c.post_id = ps.post_id
        WHERE lower(c.subreddit) = ANY(:subs)
          AND ps.value_score >= 6.0
          AND (
                c.body ILIKE ANY(:patterns)
                OR lower(p.title) ILIKE ANY(:patterns)
                OR lower(COALESCE(p.body, '')) ILIKE ANY(:patterns)
              )
          AND (:has_exclude = FALSE OR NOT (
                lower(c.body) ILIKE ANY(:exclude_patterns)
                OR lower(p.title) ILIKE ANY(:exclude_patterns)
                OR lower(COALESCE(p.body, '')) ILIKE ANY(:exclude_patterns)
              ))
          AND (:has_req = FALSE OR (
                lower(c.body) ILIKE ANY(:req_patterns)
                OR lower(p.title) ILIKE ANY(:req_patterns)
                OR lower(COALESCE(p.body, '')) ILIKE ANY(:req_patterns)
              ))
          AND LENGTH(c.body) > 20
          AND c.created_utc >= NOW() - (interval '1 day' * :days)
          AND NOT EXISTS (
            SELECT 1 FROM noise_labels nl
            WHERE nl.content_type = 'comment'
              AND nl.content_id = c.id
          )
        ORDER BY c.score DESC NULLS LAST
        LIMIT :limit
        """
    )
    
    try:
        rows = await session.execute(sql, {
            "subs": subs, 
            "patterns": all_patterns, 
            "exclude_patterns": exclude_patterns,
            "has_exclude": has_exclude,
            "req_patterns": req_patterns,
            "has_req": has_req,
            "limit": limit, 
            "days": fallback_days if use_fallback else days
        })
        results = rows.fetchall()
    except Exception as e:
        print(f"⚠️ Comment Fetch Error: {e}")
        results = []

    # If V1 filtered comments are too few, fallback to raw search (Legacy)
    if len(results) < 20:
        print("⚠️ Not enough V1-backed comments, falling back to raw search.")
        sql_fallback = text(
            """
            SELECT c.id, c.author_id, c.author_name, c.body, c.subreddit, c.source_post_id, c.reddit_comment_id, c.permalink, c.created_utc, c.score
            FROM comments c
            JOIN posts_raw p ON c.post_id = p.id
            WHERE lower(c.subreddit) = ANY(:subs)
              AND (
                    c.body ILIKE ANY(:patterns)
                    OR lower(p.title) ILIKE ANY(:patterns)
                    OR lower(COALESCE(p.body, '')) ILIKE ANY(:patterns)
                  )
              AND (:has_exclude = FALSE OR NOT (
                    lower(c.body) ILIKE ANY(:exclude_patterns)
                    OR lower(p.title) ILIKE ANY(:exclude_patterns)
                    OR lower(COALESCE(p.body, '')) ILIKE ANY(:exclude_patterns)
                  ))
              AND (:has_req = FALSE OR (
                    lower(c.body) ILIKE ANY(:req_patterns)
                    OR lower(p.title) ILIKE ANY(:req_patterns)
                    OR lower(COALESCE(p.body, '')) ILIKE ANY(:req_patterns)
                  ))
              AND LENGTH(c.body) > 20
              AND c.created_utc >= NOW() - (interval '1 day' * :days)
            ORDER BY c.score DESC NULLS LAST
            LIMIT :limit
            """
        )
        rows = await session.execute(sql_fallback, {
            "subs": subs, 
            "patterns": all_patterns, 
            "exclude_patterns": exclude_patterns,
            "has_exclude": has_exclude,
            "req_patterns": req_patterns,
            "has_req": has_req,
            "limit": limit, 
            "days": fallback_days
        })
        results = rows.fetchall()

    raw: list[dict[str, str]] = []
    promotion_flags = ("promotion", "giveaway", "coupon", "promo code", "discount code")
    unrelated_flags = ("cast iron", "cookware", "skillet", "pan", "pot", "wok", "frying pan")
    min_len_other = fallback_min_len_other or COMMENTS_CFG.get("fallback_min_len_other", 80)
    
    for r in results:
        body = getattr(r, "body", None)
        if not body:
            continue
        lower_body = body.lower()
        if not use_fallback and any(flag in lower_body for flag in promotion_flags):
            continue
        if not use_fallback and any(flag in lower_body for flag in unrelated_flags):
            continue
        cls = classify_category_aspect(body)
        if cls.category == Category.OTHER:
            if not use_fallback:
                continue
            if len(lower_body) < min_len_other:
                continue
        permalink = normalize_reddit_url(permalink=getattr(r, "permalink", None), url=None)
        created_at = getattr(r, "created_utc", None)
        comment_score = getattr(r, "score", 0)
        raw.append(
            {
                "id": str(getattr(r, "reddit_comment_id", "")),
                "author_id": getattr(r, "author_id", None),
                "author_name": getattr(r, "author_name", None),
                "body": body,
                "subreddit": getattr(r, "subreddit", ""),
                "post_id": getattr(r, "source_post_id", ""),
                "comment_id": getattr(r, "reddit_comment_id", ""),
                "permalink": permalink,
                "url": permalink,
                "created_at": created_at.isoformat() if created_at else None,
                "comment_score": int(comment_score or 0),
            }
        )

    if not raw:
        return []

    dedup_threshold = dedup_threshold if dedup_threshold is not None else _load_dedup_threshold(
        Path("config") / "deduplication.yaml"
    )
    dedup_input = [
        {
            "id": item["id"],
            "title": item["body"][:50],
            "summary": item["body"],
            "score": 0,
            "num_comments": 0,
        }
        for item in raw
    ]
    deduped = deduplicate_posts(dedup_input, threshold=dedup_threshold)
    kept_ids = {str(p.get("id")) for p in deduped if p.get("id")}
    deduped_out = [item for item in raw if item["id"] in kept_ids]
    
    if len(deduped_out) < fallback_threshold_comments and not use_fallback:
        print(f"⚠️ Comments below threshold ({len(deduped_out)}<{fallback_threshold_comments}), widening search window.")
        return await _fetch_sample_comments(
            session,
            subs,
            keywords,
            days=days,
            limit=min(limit * 2, 180),
            dedup_threshold=dedup_threshold,
            per_sub_comment_cap=40,
            fallback_threshold_comments=fallback_threshold_comments,
            fallback_days=fallback_days,
            use_fallback=True,
            fallback_min_len_other=min_len_other,
            exclude_keywords=exclude_keywords,
            required_entities=required_entities,
        )
    
    bucketed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in deduped_out:
        sub = item.get("subreddit", "").lower()
        if len(bucketed[sub]) < per_sub_comment_cap:
            bucketed[sub].append(item)
    deduped_out = [it for items in bucketed.values() for it in items]
    print(f"🧹 Deduplication: Reduced {len(raw)} -> {len(deduped_out)} comments.")

    extractor = QuoteExtractor()
    extractor.MAX_LEN = 300
    keywords_set = {k.lower() for k in keywords[:5] if k}
    quotes: list[dict[str, str]] = []
    
    for item in deduped_out:
        best_qr = None
        for sentence in extractor._iter_sentences([item["body"]]):
            qr = extractor._build_scored_quote(sentence, keywords_set, source="comment")
            if qr and (best_qr is None or qr.score > best_qr.score):
                best_qr = qr
        
        if best_qr is None:
            if len(item["body"]) <= extractor.MAX_LEN:
                best_qr = extractor._build_scored_quote(item["body"], keywords_set, source="comment")
        
        if best_qr is None:
            continue
            
        quote_text = best_qr.text
        if item.get("permalink"):
            quote_text = f"{quote_text} [🔗]({item['permalink']})"
        
        quotes.append(
            {
                "quote_id": item.get("comment_id"),
                "comment_id": item.get("comment_id"),
                "post_id": item.get("post_id"),
                "author_id": item.get("author_id"),
                "author_name": item.get("author_name"),
                "text": quote_text,
                "text_snippet": quote_text,
                "score": best_qr.score,
                "sentiment": best_qr.sentiment,
                "relevance": best_qr.relevance,
                "subreddit": item.get("subreddit", ""),
                "permalink": item.get("permalink", ""),
                "created_at": item.get("created_at"),
                "comment_score": item.get("comment_score"),
            }
        )

    quotes.sort(key=lambda x: (-x["score"], -x["relevance"]))
    return quotes[:limit]


async def _jit_label_comments(
    session,
    topic_tokens: set[str],
    exclusion_tokens: set[str],
    days: int,
    limit: int = 5000,
) -> int:
    if not topic_tokens:
        return 0
    search_query = " | ".join(topic_tokens)
    exclude_query = " | ".join(exclusion_tokens)
    has_exclude = bool(exclude_query)
    sql = text(
        """
        WITH target AS (
            SELECT c.id, c.reddit_comment_id
            FROM comments c
            LEFT JOIN content_labels cl
                ON cl.content_type = 'comment'
               AND cl.content_id = c.id
            WHERE c.created_utc >= NOW() - (interval '1 day' * :days)
              AND cl.id IS NULL
              AND to_tsvector('english', COALESCE(c.body, '')) @@ to_tsquery('english', :search_query)
              AND (
                    :has_exclude = FALSE OR NOT (
                        to_tsvector('english', COALESCE(c.body, ''))
                        @@ to_tsquery('english', :exclude_query)
                    )
                  )
            LIMIT :limit
        )
        SELECT reddit_comment_id FROM target
        """
    )
    res = await session.execute(
        sql,
        {
            "days": days,
            "search_query": search_query,
            "has_exclude": has_exclude,
            "exclude_query": exclude_query or "''",
            "limit": limit,
        },
    )
    ids = [row.reddit_comment_id for row in res.fetchall()]
    print(f"🔎 JIT Labeling candidate comments: {len(ids)} (window={days}d)")
    if not ids:
        return 0
    processed = await classify_and_label_comments(session, ids)
    await session.commit()
    print(f"🏷️  JIT Labeling: Processed {processed} comments for topic tokens.")
    return processed


def _extract_recommended_keywords(report_text: str, fallback: list[str]) -> list[str]:
    candidates: set[str] = set()
    if report_text:
        pattern = re.findall(r"(?:关键词|keywords?)[:：]\s*([^\n]+)", report_text, flags=re.IGNORECASE)
        for segment in pattern:
            for token in re.split(r"[、,;，]|\\s+", segment):
                t = token.strip().lower()
                if t and len(t) > 1:
                    candidates.add(t)
        for line in report_text.splitlines():
            if "关键词" in line.lower() or "keyword" in line.lower():
                for token in re.split(r"[、,;，]|\\s+", line):
                    t = token.strip().lower()
                    if t and len(t) > 1 and "keyword" not in t and "关键词" not in t:
                        candidates.add(t)
    if not candidates and fallback:
        for t in fallback[:10]:
            if t and isinstance(t, str):
                candidates.add(t.strip().lower())
    return list(candidates)[:20]


async def _insert_semantic_candidates(keywords: list[str]) -> int:
    if not keywords:
        return 0
    inserted = 0
    try:
        async with SessionFactory() as session:
            for term in keywords:
                await session.execute(
                    text(
                        """
                        INSERT INTO semantic_candidates 
                        (term, status, frequency, source, first_seen_at, last_seen_at)
                        VALUES (:term, 'pending', 1, 'report_gen', NOW(), NOW())
                        ON CONFLICT (term) DO UPDATE 
                        SET frequency = semantic_candidates.frequency + 1,
                            last_seen_at = NOW()
                        """
                    ),
                    {"term": term},
                )
                inserted += 1
            await session.commit()
    except Exception as exc:
        print(f"⚠️ semantic_candidates insert failed: {exc}")
        return 0
    return inserted


def _load_community_roles(config_path: Path) -> dict:
    try:
        if not config_path.exists():
            return {}
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return payload.get("roles", {})
    except Exception as e:
        print(f"⚠️ Failed to load community roles: {e}")
        return {}


def build_facts_slice_for_report(facts: dict[str, Any]) -> dict[str, Any]:
    """
    Slim down the facts dictionary for LLM consumption to save tokens.
    Retains only high-signal components for the report generation context.
    """
    # facts_v2 package path
    if "aggregates" in facts and "meta" in facts:
        aggregates = facts.get("aggregates", {}) or {}
        business_signals = facts.get("business_signals", {}) or {}
        source_range = (facts.get("data_lineage", {}) or {}).get("source_range", {}) or {}

        communities = aggregates.get("communities", []) or []
        if isinstance(communities, list):
            top_communities = communities[:8]
        else:
            top_communities = []

        comments = facts.get("sample_comments_db", []) or []
        top_comments = comments[:30] if isinstance(comments, list) else []

        posts = facts.get("sample_posts_db", []) or []
        top_posts = posts[:20] if isinstance(posts, list) else []

        pains = business_signals.get("high_value_pains", []) or []
        pain_clusters = pains[:5] if isinstance(pains, list) else []

        brand_pain = business_signals.get("brand_pain", []) or []
        brand_pain = brand_pain[:10] if isinstance(brand_pain, list) else []

        overall = {
            "topic": (facts.get("meta", {}) or {}).get("topic"),
            "total_posts": source_range.get("posts"),
            "total_comments": source_range.get("comments"),
            "trend_analysis": aggregates.get("trend_analysis"),
            "trend_source": aggregates.get("trend_source"),
        }

        return {
            "overall": overall,
            "community_stats": top_communities,
            "brand_pain": brand_pain,
            "pain_clusters": pain_clusters,
            "market_saturation": business_signals.get("market_saturation", []),
            "business_signals": business_signals,
            "sample_posts_db": top_posts,
            "sample_comments_db": top_comments,
            "diagnostics": facts.get("diagnostics"),
        }

    # 1. Communities: Top 8 sorted by score
    communities = facts.get("communities", [])
    # Sort by final_score desc if available
    communities.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    top_communities = communities[:8]
    
    # 2. Sample Comments: Top 30
    # Already sorted by relevance/score in fetcher
    comments = facts.get("sample_comments_db", [])
    top_comments = comments[:30]
    
    # 3. Brand Pain: Top 10
    brand_pain = facts.get("brand_pain", [])[:10]
    
    # 4. Pain Clusters: Top 5
    pain_clusters = facts.get("pain_clusters", [])[:5]
    
    # 5. Business Signals (Critical)
    business_signals = facts.get("business_signals", {})
    
    # 6. Overall Metrics
    overall = {
        "global_ps_ratio": facts.get("global_ps_ratio"),
        "total_posts": facts.get("total_posts"),
        "total_comments": facts.get("total_comments"),
        "topic": facts.get("topic"),
        "trend_analysis": facts.get("trend_analysis"),
        "trend_source": facts.get("trend_source"),
    }
    
    # Construct Sliced Dict
    sliced = {
        "overall": overall,
        "community_stats": top_communities,
        "brand_pain": brand_pain,
        "pain_clusters": pain_clusters,
        "market_saturation": facts.get("market_saturation", []),
        "business_signals": business_signals,
        "sample_comments_db": top_comments,
        "market_landscape": facts.get("market_landscape"),
        "topic_keywords": facts.get("topic_keywords", [])[:30],
        "price_analysis": facts.get("price_analysis"),
        "usage_context": facts.get("usage_context"),
        "community_personas": facts.get("community_personas"),
    }
    return sliced


def _load_community_roles(config_path: Path) -> dict:
    try:
        if not config_path.exists():
            return {}
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return payload.get("roles", {})
    except Exception as e:
        print(f"⚠️ Failed to load community roles: {e}")
        return {}


def _convert_decimals_to_floats(obj: Any) -> Any:
    """Recursively converts Decimal objects to floats within a dict or list."""
    if isinstance(obj, list):
        return [_convert_decimals_to_floats(elem) for elem in obj]
    elif isinstance(obj, dict):
        return {key: _convert_decimals_to_floats(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def _resolve_mode(raw_mode: str | None, profile: TopicProfile | None) -> str:
    cleaned = str(raw_mode or "").strip().lower()
    if cleaned and cleaned != "auto":
        return cleaned
    profile_mode = str(getattr(profile, "mode", "") or "").strip().lower()
    if profile_mode in {"market_insight", "operations"}:
        return profile_mode
    return "market_insight"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate T1 market report (template-driven).")
    parser.add_argument("--topic", default=os.getenv("REPORT_TOPIC", "跨境电商支付/收款解决方案"), help="本次话题/赛道描述")
    parser.add_argument("--product-desc", default=os.getenv("PRODUCT_DESC", "面向跨境电商卖家/服务商的收款与资金管理方案"), help="产品/赛道说明")
    parser.add_argument("--days", type=int, default=365, help="时间窗口（天）")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL_NAME", getattr(settings, "llm_model_name", "gpt-4o-mini")), help="LLM 模型名")
    parser.add_argument("--out", default="reports/t1-auto.md", help="输出路径（相对 backend 根）")
    parser.add_argument("--run-quality", action="store_true", help="生成后自动运行 stage4-quality（t1-data-audit + content-acceptance）")
    parser.add_argument(
        "--mode",
        choices=["auto", "market_insight", "operations"],
        default="auto",
        help="分析模式：auto(默认，优先用 TopicProfile.mode) / market_insight / operations",
    )
    parser.add_argument("--skip-llm", action="store_true", help="仅生成 facts/facts_slice，不调用 LLM 阶段")
    args = parser.parse_args()

    print("⚠️  Legacy 脚本：主链路请以 /api/analyze 为准，此脚本仅用于离线验证/实验。")

    run_id = str(uuid.uuid4())
    snapshot_id = str(uuid.uuid4())
    base_dir = Path(__file__).resolve().parent.parent  # backend/
    config_root = base_dir.parent / "config"
    config_paths = [
        config_root / "vertical_overrides.yaml",
        config_root / "scoring_rules.yaml",
        config_root / "crossborder_scoring.yml",
        config_root / "thresholds.yaml",
        base_dir.parent / "config" / "scoring_templates.yaml",
    ]
    config_hash = _hash_files(config_paths)
    dedup_threshold = _load_dedup_threshold(config_root / "deduplication.yaml")
    scoring_loader = ScoringRulesLoader(config_root / "scoring_rules.yaml")
    rules_loaded = scoring_loader.load()
    if not rules_loaded or not getattr(rules_loaded, "positive_keywords", None):
        raise ValueError("Scoring rules not loaded! Check config/scoring_rules.yaml")
    opportunity_scorer = OpportunityScorer(loader=scoring_loader)
    blacklist_config = BlacklistConfig(str(config_root / "community_blacklist.yaml"))
    if not hasattr(blacklist_config, "whitelisted_communities"):
        blacklist_config.whitelisted_communities = set()
    contextual_filters = getattr(blacklist_config, "contextual_filters", []) or []
    
    # Load Roles
    roles = _load_community_roles(config_root / "community_roles.yaml")
    ops_role = roles.get("operations", {})
    ops_comms = {c.lower() for c in ops_role.get("communities", [])}

    # 1) Topic Profile (preferred) → 2) Semantic Expansion (fallback)
    active_profile: TopicProfile | None = None
    profile_allowed_communities: list[str] = []
    profile_required_entities: list[str] = []
    topic_kw_for_search: list[str] = []
    topic_kw_for_fetch: list[str] = []

    vertical = "other"
    topic_tokens: set[str] = set()
    exclusion_tokens: set[str] = set()

    topic_profiles = load_topic_profiles()
    active_profile = match_topic_profile(args.topic, topic_profiles)

    if active_profile:
        print(f"🎯 Topic Profile Active: {active_profile.topic_name}")
        if active_profile.preferred_days and args.days < active_profile.preferred_days:
            print(
                f"🕒 Narrow topic window: extending {args.days}d -> {active_profile.preferred_days}d (topic profile)"
            )
            args.days = active_profile.preferred_days
        vertical = (active_profile.vertical or "other").strip().lower()
        profile_allowed_communities = active_profile.allowed_communities
        profile_required_entities = active_profile.required_entities_any
        topic_kw_for_search = build_search_keywords(active_profile, args.topic)
        topic_kw_for_fetch = build_fetch_keywords(active_profile, args.topic)
        # topic_tokens / exclusion_tokens 用于 DB 的全文检索（to_tsquery），必须是“单词级”token，不能带空格
        for kw in topic_kw_for_search:
            if kw:
                topic_tokens.update(_tokenize_topic(kw))
        for ex in topic_profile_blocklist_keywords(active_profile):
            if ex:
                exclusion_tokens.update(_tokenize_topic(ex))
    else:
        topic_tokens, exclusion_tokens, vertical = await _expand_topic_semantically(
            args.topic, model="openai/gpt-4o-mini", blacklist_config=blacklist_config
        )
        topic_kw_for_search = list(topic_tokens)
        topic_kw_for_fetch = topic_kw_for_search

    resolved_mode = _resolve_mode(args.mode, active_profile)
    if args.mode == "auto":
        print(f"🧭 Auto mode resolved -> {resolved_mode}")
    args.mode = resolved_mode

    # Apply Contextual Filters based on Vertical
    def _apply_contextual_filters(vertical_tag: str) -> set[str]:
        dyn_block: set[str] = set()
        vt = (vertical_tag or "other").strip().lower()
        for group in contextual_filters:
            comms = {c.strip().lower() for c in group.get("communities", []) if c}
            allowed = {v.strip().lower() for v in group.get("allowed_verticals", []) if v}
            if vt and vt in allowed:
                continue
            dyn_block.update(comms)
        return dyn_block

    dynamic_block = _apply_contextual_filters(vertical)

    if args.mode == "market_insight":
        # Topic Profile 明确声明 allowed_communities 时，视为“卖家侧/B2B”赛道：不再强行屏蔽 seller 社区。
        if active_profile and profile_allowed_communities:
            print("🛡️  Mode: Market Insight (profile override). Keeping seller communities enabled.")
        else:
            print(f"🛡️  Mode: Market Insight. Blocking {len(ops_comms)} seller communities.")
            blacklist_config.blacklisted_communities.update(ops_comms)
    elif args.mode == "operations":
        print(f"💼 Mode: Operations. Focusing on {len(ops_comms)} seller communities.")
        blacklist_config.blacklisted_communities.difference_update(ops_comms)
        # 强制注入核心运营社区白名单，屏蔽泛社区噪声
        ops_core = VERTICAL_CORE_WHITELIST.get("operations", set())
        ops_noise = {"r/frugal", "r/financialindependence", "r/churning", "r/buyitforlife", "r/relationships", "r/relationship_advice"}
        blacklist_config.whitelisted_communities.update({c.lower() for c in ops_core})
        blacklist_config.blacklisted_communities.update({c.lower() for c in ops_noise})

    # Topic Profile allowlist 永远优先：确保不会被 mode/contextual block 误杀
    if active_profile and profile_allowed_communities:
        allowed_norm = {normalize_subreddit(c) for c in profile_allowed_communities if c}
        blacklist_config.blacklisted_communities.difference_update(allowed_norm)
        blacklist_config.whitelisted_communities.update(allowed_norm)

    # Merge dynamic contextual blacklist
    if dynamic_block:
        print(f"🧱 Contextual blocklist applied for vertical '{vertical}': +{len(dynamic_block)} communities.")
        blacklist_config.blacklisted_communities.update(dynamic_block)

    # 垂直硬黑名单（手电/EDC 等）——先收紧，覆盖不足时再放宽
    strict_vertical_blacklist: set[str] = set()
    if vertical in {"edc", "consumer_electronics"}:
        strict_vertical_blacklist = {
            "r/financialindependence",
            "r/frugal",
            "r/povertyfinance",
            "r/personalfinance",
            "r/cleaningtips",
            "r/cooking",
        }
        blacklist_config.blacklisted_communities.update(strict_vertical_blacklist)


    _print_config_summary(blacklist_config, dedup_threshold, scoring_loader)
    clusters: list[Any] = []
    pain_tree: list[dict[str, Any]] = []
    context_relax = False

    async with SessionFactory() as session:
        jit_days = min(args.days, 30)
        await _jit_label_comments(session, topic_tokens, exclusion_tokens, days=jit_days, limit=5000)
        await label_posts_recent(session, since_days=jit_days, limit=2000)
        
        relevance_map = await fetch_topic_relevant_communities(
            session,
            topic=args.topic,
            topic_tokens=topic_tokens,
            exclusion_tokens=exclusion_tokens,
            days=args.days,
            min_relevance_score=5,
        )
        if active_profile:
            relevance_map = filter_relevance_map_with_profile(relevance_map or {}, active_profile)
        # Dynamic contextual allow/block based on topic/off-topic hit ratio (semantic-driven)
        dynamic_blacklist: set[str] = set()
        dynamic_whitelist: set[str] = set()
        vertical_cfg = _get_vertical_cfg(vertical or "other")
        dyn_white_cap = vertical_cfg.get("dynamic_whitelist_cap", MAX_DYNAMIC_WHITELIST)
        dyn_black_cap = vertical_cfg.get("dynamic_blacklist_cap", MAX_DYNAMIC_BLACKLIST)
        context_scores = await _score_communities_contextually(
            session,
            subs=list((relevance_map or {}).keys())[:120],
            topic_tokens=topic_tokens,
            vertical=vertical or "other",
            days=args.days,
            limit=120,
        )
        # Force candidate set constraint: only from relevance_map
        candidate_set = {k.lower() if k else "" for k in (relevance_map or {}).keys()}
        hard_whitelist = set(vertical_cfg.get("core_whitelist", VERTICAL_CORE_WHITELIST.get(vertical or "", set())))
        hard_blacklist = set(vertical_cfg.get("hard_blacklist", VERTICAL_CORE_BLACKLIST.get(vertical or "", set())))

        # Sort by semantic score descending
        sorted_by_sim = sorted(
            context_scores.items(),
            key=lambda kv: kv[1].get("sim_score", 0.0),
            reverse=True,
        )
        for sub, score in sorted_by_sim:
            if candidate_set and sub not in candidate_set:
                continue
            if sub in blacklist_config.blacklisted_communities:
                continue
            if sub in hard_blacklist:
                continue
            if len(dynamic_whitelist) >= dyn_white_cap:
                break
            t_hits = score.get("topic_hits", 0.0)
            off_ratio = score.get("off_ratio", 0.0)
            if t_hits >= MIN_TOPIC_HITS and off_ratio <= MAX_OFFTOPIC_RATIO:
                dynamic_whitelist.add(sub)

        # Blacklist: high off_ratio with low topic_hits
        for sub, score in sorted_by_sim:
            if candidate_set and sub not in candidate_set:
                continue
            if sub in hard_blacklist:
                dynamic_blacklist.add(sub)
                continue
            if len(dynamic_blacklist) >= dyn_black_cap:
                break
            t_hits = score.get("topic_hits", 0.0)
            off_ratio = score.get("off_ratio", 0.0)
            if t_hits < MIN_TOPIC_HITS and off_ratio >= MAX_OFFTOPIC_RATIO:
                dynamic_blacklist.add(sub)

        # Apply dynamic filters: config whitelist always wins
        config_whitelist = {c.lower() for c in getattr(blacklist_config, "whitelisted_communities", set())}
        dynamic_blacklist = {c for c in dynamic_blacklist if c not in config_whitelist}
        # Add hard vertical whitelist
        dynamic_whitelist.update({w.lower() for w in hard_whitelist})
        # Enforce hard blacklist
        dynamic_blacklist.update({b.lower() for b in hard_blacklist})

        if dynamic_blacklist:
            print(f"🚧 Dynamic blacklist: {sorted(list(dynamic_blacklist))[:10]} (+{len(dynamic_blacklist)})")
            blacklist_config.blacklisted_communities.update(dynamic_blacklist)
        if dynamic_whitelist:
            print(f"✅ Dynamic whitelist: {sorted(list(dynamic_whitelist))[:10]} (+{len(dynamic_whitelist)})")
            blacklist_config.whitelisted_communities.update(dynamic_whitelist)

        if args.mode == "operations":
            original_count = len(relevance_map)
            # Filter to keep only operations communities (handle r/ prefix variations)
            filtered_map = {}
            for k, v in relevance_map.items():
                norm_k = k.lower()
                norm_k_no_prefix = norm_k.replace("r/", "")
                if norm_k in ops_comms or norm_k_no_prefix in ops_comms:
                    filtered_map[k] = v
            relevance_map = filtered_map
            print(f"💼 Mode: Operations. Filtered communities from {original_count} to {len(relevance_map)}.")

        candidate_subs = _pick_relevant_subreddits(relevance_map, limit=120)
        stats = await build_stats_snapshot(
            session,
            subreddits=candidate_subs or None,
            days=args.days,
        )
        trend_data, trend_source, time_window_used, trend_degraded = await _load_trend_with_fallback(
            session, topic_tokens=list(topic_tokens), days=args.days
        )
        entity_sentiment = await build_entity_sentiment_matrix(
            session,
            topic_tokens=topic_tokens,
            months=12,
            min_mentions=3,
        )
        brand_sentiment_top = _top_brand_sentiment(entity_sentiment)

        stats_path = await write_snapshot_to_file(
            session,
            subreddits=candidate_subs or None,
            days=args.days,
        )
        
        # 取核心社区列表，用于样例评论抽取
        selected_communities = await _select_relevant_communities(
            session,
            stats,
            topic_tokens,
            exclusion_tokens,
            relevance_map,
            blacklist_config,
            limit=10,
            allowed_communities=profile_allowed_communities,
        )
        # 强制注入垂直核心社区，避免被筛掉
        core_whitelist = set(vertical_cfg.get("core_whitelist", VERTICAL_CORE_WHITELIST.get(vertical or "", set())))
        existing = {c.get("name", "").lower() for c in selected_communities}
        for comm in core_whitelist:
            if comm.lower() not in existing:
                selected_communities.append({"name": comm, "score": 1.0})
        # 保证至少 5 个
        if len(selected_communities) < 5:
            selected_communities = (selected_communities + list(core_whitelist))[:5]
        core_subs = [c.get("name") for c in selected_communities if c.get("name")]

        # 覆盖不足时放宽垂直硬黑名单
        if strict_vertical_blacklist and len(core_subs) < 5:
            context_relax = True
            blacklist_config.blacklisted_communities.difference_update(strict_vertical_blacklist)
            dynamic_blacklist.difference_update(strict_vertical_blacklist)
            print("⚠️ Coverage <5, relaxing strict vertical blacklist.")
            selected_communities = await _select_relevant_communities(
                session,
                stats,
                topic_tokens,
                exclusion_tokens,
                relevance_map,
                blacklist_config,
            )
            core_subs = [c.get("name") for c in selected_communities]
            if vertical in {"edc", "consumer_electronics"}:
                existing = {c.get("name", "").lower() for c in selected_communities}
                for comm in EDC_CORE_COMMUNITIES:
                    if comm.lower() not in existing:
                        selected_communities.append({"name": comm, "score": 1.0})
                selected_communities = selected_communities[: max(5, len(selected_communities))]
                core_subs = [c.get("name") for c in selected_communities]

        # --- Persona Generation for Top 3 communities ---
        community_personas: list[dict[str, Any]] = []
        if selected_communities:
            print("🎭 Generating community personas for Top 3...")
            top_persona_subs = [c.get("name") for c in selected_communities[:3] if c.get("name")]
            if top_persona_subs:
                try:
                    llm_client_for_persona = OpenAIChatClient(model=args.model)
                    persona_gen = PersonaGenerator(llm_client=llm_client_for_persona)
                    personas_raw = await persona_gen.generate_batch(session, top_persona_subs)
                    community_personas = [p.to_dict() for p in personas_raw]
                except Exception as persona_exc:
                    print(f"⚠️ Persona LLM failed, fallback to rule-based: {persona_exc}")
                    for sub in top_persona_subs:
                        community_personas.append(
                            {
                                "community": sub,
                                "persona_label": "Active Enthusiasts",
                                "traits": ["community-regulars", "topic-focused"],
                                "strategy": "Use rule-based signals until LLM recovers",
                                "confidence": 0.2,
                            }
                        )
        
        # Phase 5.2: Fetch need distribution for selected communities
        need_distribution = await _fetch_need_distribution(session, core_subs, args.days)

        # 语义痛点聚类（密度驱动），优先核心社区
        clusters = await cluster_pain_points_auto(
            session,
            since_days=args.days,
            subreddits=core_subs,
            limit_per_source=400,
            min_clusters=3,
            max_clusters=6,
        )
        pain_tree = [
            {
                "root_cause": c.get("topic", "pain cluster"),
                "sub_issues": (c.get("samples") or c.get("top_communities") or [])[:3],
                "summary": f"freq={c.get('total_frequency', 0)}, neg_mean={c.get('negative_mean', 0)}",
            }
            for c in clusters
        ]

        topic_keywords_override: list[str] = []
        corpus = []
        for c in clusters:
            corpus.extend([s for s in c.get("samples", []) if isinstance(s, str)])
        if corpus:
            try:
                kw = await extract_keywords("\n".join(corpus), max_keywords=10)
                topic_keywords_override = kw.keywords
            except Exception as exc:
                print(f"⚠️ Keyword extraction failed, fallback to defaults: {exc}")

        # ---- Final communities assembling ----
        sim_lookup = {k: v.get("sim_score", 0.0) for k, v in context_scores.items()}
        final_comm: list[dict[str, Any]] = []
        seen: set[str] = set()
        allow_by_profile = (lambda name: True) if not active_profile else (
            lambda name: topic_profile_allows_community(active_profile, name)
        )
        core_list_for_final: list[str] = []
        if args.mode == "operations":
            core_list_for_final = list(OPS_CORE_COMMUNITIES)
        elif vertical in {"edc", "consumer_electronics"}:
            core_list_for_final = list(vertical_cfg.get("core_whitelist", EDC_CORE_COMMUNITIES))
        # 1) core hard whitelist (EDC/flashlight or ops)
        for comm in core_list_for_final:
            if not allow_by_profile(comm):
                continue
            key = comm.lower()
            if args.mode == "operations" and key in OPS_EXCLUDE_COMMUNITIES:
                continue
            if key in seen:
                continue
            final_comm.append({"name": comm, "score": sim_lookup.get(key, 1.0)})
            seen.add(key)
        # 2) dynamic whitelist (semantic sorted)
        dyn_sorted = sorted(
            list(dynamic_whitelist),
            key=lambda c: sim_lookup.get(c, 0.0),
            reverse=True,
        )
        for comm in dyn_sorted:
            if not allow_by_profile(comm):
                continue
            key = comm.lower()
            if args.mode == "operations" and key not in OPS_CORE_COMMUNITIES:
                continue
            if key in seen:
                continue
            final_comm.append({"name": comm, "score": sim_lookup.get(key, 0.0)})
            seen.add(key)
        # 3) selected communities (keep original order)
        for comm in selected_communities:
            name = (comm.get("name") or "").lower()
            if name and not allow_by_profile(name):
                continue
            if args.mode == "operations" and name not in OPS_CORE_COMMUNITIES:
                continue
            if not name or name in seen:
                continue
            final_comm.append(comm)
            seen.add(name)
        # Cap to 10, ensure at least 5 for edc/ops vertical
        final_comm = final_comm[:10] if len(final_comm) > 10 else final_comm
        if len(final_comm) < 5 and core_list_for_final:
            for comm in core_list_for_final:
                key = comm.lower()
                if key in seen:
                    continue
                final_comm.append({"name": comm, "score": sim_lookup.get(key, 0.0)})
                seen.add(key)
                if len(final_comm) >= 5:
                    break
        # 最终再过滤一次 ops 排除社区，防止残留，并将核心社区优先排序
        if args.mode == "operations":
            core_set = [c.lower() for c in OPS_CORE_COMMUNITIES]
            filtered = [
                c for c in final_comm
                if (c.get("name") or "").lower() in core_set
            ]
            # 硬保留核心社区，若缺则补齐
            existing = { (c.get("name") or "").lower(): c for c in filtered }
            for core in OPS_CORE_COMMUNITIES:
                key = core.lower()
                if key in existing:
                    continue
                filtered.append({"name": core, "score": sim_lookup.get(key, 1.0)})
            # 核心置顶，截断10
            filtered.sort(key=lambda x: (0 if (x.get("name") or "").lower() in core_set else 1, -x.get("score", 0)))
            final_comm = filtered[:10]
        core_subs = [c.get("name") for c in final_comm if c.get("name")]

        # 动态品牌补全 + DB 回溯
        llm_brands = await _fetch_top_brands_from_llm(args.topic, args.model)
        brand_backfill = await _backfill_brand_mentions(session, llm_brands)

        # 竞品分层：合并品牌共现与回溯计数，使用配置化分层
        brand_counts: dict[str, dict[str, Any]] = {}
        for b in getattr(stats, "brand_pain_cooccurrence", []) or []:
            name = str(getattr(b, "brand", "") or "").strip()
            if not name:
                continue
            key = name.lower()
            brand_counts.setdefault(key, {"name": name, "mentions": 0})
            brand_counts[key]["mentions"] += int(getattr(b, "mentions", 0) or 0)
        for bf in brand_backfill or []:
            name = str(bf.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            brand_counts.setdefault(key, {"name": name, "mentions": 0})
            brand_counts[key]["mentions"] += int(bf.get("mentions") or 0)
        competitors_layered = assign_competitor_layers(list(brand_counts.values()))
        market_landscape = {
            "layers": build_layer_summary(competitors_layered),
            "items": competitors_layered,
        }

        if not active_profile:
            topic_kw_for_search = topic_keywords_override or list(topic_tokens)
            topic_kw_for_fetch = topic_kw_for_search
        # 针对手电筒/EDC 赛道补充关键词，提升 solutions/上下文召回
        if vertical in {"edc", "consumer_electronics"}:
            edc_kw = set(vertical_cfg.get("keywords", [])) or {"beam", "throw", "hotspot", "charger", "battery", "runtime", "torch", "head", "headlamp", "tailcap", "lumens"}
            topic_kw_for_search = list({*topic_kw_for_search, *edc_kw})
        # operations 模式补充运营线索词，提升方案召回
        if args.mode == "operations":
            ops_solution_kw = {
                "appeal", "reinstated", "plan of action", "ticket", "support", "contact amazon",
                "submit", "escalate", "policy fix", "case", "resolved", "case id", "seller support",
                "suspension lifted", "verification", "invoice", "supply chain", "tracking", "shipment",
                "inbound", "logistics", "suspension", "ban", "relist", "reactivate",
                "fee", "review", "claim", "insurance", "performance team", "compliance", "notice",
                "policy violation", "asin", "poa", "appeal letter", "documentation", "proof", "invoice",
                "supply chain", "policy strike", "restriction", "case log", "case number"
            }
            topic_kw_for_search = list({*topic_kw_for_search, *ops_solution_kw})

        comment_cfg = {**COMMENTS_CFG, **(vertical_cfg.get("comments", {}) or {})}
        post_cfg = {**POSTS_CFG, **(vertical_cfg.get("posts", {}) or {})}
        solution_cfg = {**SOLUTIONS_CFG, **(vertical_cfg.get("solutions", {}) or {})}
        # 窄题扩样本：兜底窗口至少覆盖 profile.preferred_days
        if active_profile and active_profile.preferred_days:
            comment_cfg["fallback_days"] = max(
                int(comment_cfg.get("fallback_days", 540) or 540),
                int(active_profile.preferred_days),
            )
            post_cfg["fallback_days"] = max(
                int(post_cfg.get("fallback_days", 540) or 540),
                int(active_profile.preferred_days),
            )

        # Parallel fetch: Sample Comments & Top Posts (The "Flesh")
        sample_comments_db = await _fetch_sample_comments(
            session,
            core_subs,
            topic_kw_for_fetch or topic_kw_for_search,
            days=args.days,
            limit=comment_cfg.get("limit", 150),
            per_sub_comment_cap=comment_cfg.get("per_sub_cap", 40),
            fallback_threshold_comments=comment_cfg.get("fallback_threshold", 60),
            fallback_days=comment_cfg.get("fallback_days", 540),
            fallback_min_len_other=comment_cfg.get("fallback_min_len_other", 80),
            exclude_keywords=list(exclusion_tokens),
            required_entities=profile_required_entities,
        )
        if active_profile:
            sample_comments_db = list(
                filter_items_by_profile_context(
                    sample_comments_db, active_profile, text_keys=("text", "body", "title")
                )
            )

        top_posts_db, posts_fallback_used = await _fetch_top_posts(
            session,
            core_subs,
            topic_kw_for_fetch or topic_kw_for_search,
            days=args.days,
            required_entities=profile_required_entities,
            exclude_keywords=list(exclusion_tokens),
        )
        if active_profile:
            top_posts_db = list(
                filter_items_by_profile_context(top_posts_db, active_profile, text_keys=("title", "body"))
            )
        manual_data_fallback = False
        if len(sample_comments_db) < 60:
            manual_data_fallback = True
            sample_comments_db = await _fetch_sample_comments(
                session,
                core_subs,
                topic_kw_for_fetch or topic_kw_for_search,
                days=args.days,
                limit=comment_cfg.get("fallback_limit", 180),
                dedup_threshold=dedup_threshold,
                per_sub_comment_cap=comment_cfg.get("per_sub_cap", 40),
                fallback_threshold_comments=comment_cfg.get("fallback_threshold", 60),
                fallback_days=comment_cfg.get("fallback_days", 540),
                use_fallback=True,
                fallback_min_len_other=comment_cfg.get("fallback_min_len_other", 80),
                exclude_keywords=list(exclusion_tokens),
                required_entities=profile_required_entities,
            )
            if active_profile:
                sample_comments_db = list(
                    filter_items_by_profile_context(
                        sample_comments_db, active_profile, text_keys=("text", "body", "title")
                    )
                )
        if len(top_posts_db) < 30:
            manual_data_fallback = True
            extra_posts, extra_fb = await _fetch_top_posts(
                session,
                core_subs,
                topic_kw_for_fetch or topic_kw_for_search,
                limit=max(post_cfg.get("fallback_limit", 80), post_cfg.get("limit", 60)),
                days=post_cfg.get("fallback_days", 540),
                required_entities=profile_required_entities,
                exclude_keywords=list(exclusion_tokens),
            )
            top_posts_db = extra_posts or top_posts_db
            if active_profile:
                top_posts_db = list(
                    filter_items_by_profile_context(
                        top_posts_db, active_profile, text_keys=("title", "body")
                    )
                )
            posts_fallback_used = posts_fallback_used or extra_fb or True

        # Saturation Matrix
        top_brands = [v.get("name") for v in sorted(brand_counts.values(), key=lambda x: x.get("mentions", 0), reverse=True)[:10] if v.get("name")]
        saturation_matrix = SaturationMatrix()
        market_saturation_raw = await saturation_matrix.compute(
            session,
            communities=core_subs,
            brands=top_brands,
            days=args.days,
        ) if core_subs and top_brands else []
        market_saturation = [
            {
                "community": m.community,
                "overall_saturation": m.overall_saturation,
                "brands": [
                    {"brand": b.brand, "saturation": b.saturation, "status": b.status}
                    for b in (m.brands or [])
                ],
            }
            for m in (market_saturation_raw or [])
        ]

        # Business Signals
        # Merge Top Posts and Sample Comments for Extraction (Solutions are often in comments!)
        extraction_corpus = list(top_posts_db)
        # Normalize comments to look like posts for the extractor
        for c in sample_comments_db:
            extraction_corpus.append({
                "id": c.get("id"),
                "text": c.get("body") or c.get("text") or "",
                "score": 0, # Comments score handling if needed
                "num_comments": 0
            })

        # operations 模式下放宽情绪/去重阈值，适配申诉/工单语境
        ops_solution_cfg = {}
        if args.mode == "operations":
            ops_solution_cfg = {
                "sentiment_primary": -0.3,
                "sentiment_secondary": -0.5,
                "sentiment_tertiary": -0.6,
                "dedup_threshold": 0.3,
            }
        merged_solution_cfg = {**solution_cfg, **ops_solution_cfg}

        signal_extractor = SignalExtractor(solution_config=merged_solution_cfg)
        # Feed the merged corpus
        business_signals_obj = signal_extractor.extract(extraction_corpus, keywords=topic_kw_for_search)
        business_signals = {
            "high_value_pains": [p.to_dict() for p in business_signals_obj.pain_points],
            "buying_opportunities": [o.to_dict() for o in business_signals_obj.opportunities],
            "competitor_insights": [c.to_dict() for c in business_signals_obj.competitors],
            "solutions": [s.to_dict() for s in (business_signals_obj.solutions or [])],
        }
        solutions_fallback_used = False
        if len(business_signals.get("solutions", [])) < 5:
            # 兜底：放宽情绪阈值与去重阈值，尝试补足 solutions
            relaxed_cfg = {
                "sentiment_primary": solution_cfg.get("sentiment_secondary", -0.15),
                "sentiment_secondary": solution_cfg.get("sentiment_tertiary", -0.2),
                "sentiment_tertiary": min(solution_cfg.get("sentiment_tertiary", -0.2) * 1.5, -0.3),
                "dedup_threshold": min(solution_cfg.get("dedup_threshold", 0.75), 0.6),
            }
            try:
                relaxed_extractor = SignalExtractor(solution_config=relaxed_cfg)
                relaxed_obj = relaxed_extractor.extract(extraction_corpus, keywords=topic_kw_for_search)
                merged = {s["description"]: s for s in business_signals.get("solutions", []) or []}
                for sol in [s.to_dict() for s in (relaxed_obj.solutions or [])]:
                    merged.setdefault(sol["description"], sol)
                business_signals["solutions"] = list(merged.values())
                solutions_fallback_used = True
            except Exception as exc:  # pragma: no cover
                print(f"⚠️ solutions fallback failed: {exc}")
        # 第三档兜底：极度放宽情绪/去重，确保至少收集到可用方案
        if len(business_signals.get("solutions", [])) < 5:
            extreme_cfg = {
                "sentiment_primary": min(solution_cfg.get("sentiment_tertiary", -0.2) * 1.25, -0.25),
                "sentiment_secondary": min(solution_cfg.get("sentiment_tertiary", -0.2) * 1.5, -0.3),
                "sentiment_tertiary": min(solution_cfg.get("sentiment_tertiary", -0.2) * 1.8, -0.35),
                "dedup_threshold": 0.5,
            }
            try:
                extreme_extractor = SignalExtractor(solution_config=extreme_cfg)
                extreme_obj = extreme_extractor.extract(extraction_corpus, keywords=topic_kw_for_search)
                merged = {s["description"]: s for s in business_signals.get("solutions", []) or []}
                for sol in [s.to_dict() for s in (extreme_obj.solutions or [])]:
                    merged.setdefault(sol["description"], sol)
                business_signals["solutions"] = list(merged.values())
                solutions_fallback_used = True
            except Exception as exc:  # pragma: no cover
                print(f"⚠️ solutions extreme fallback failed: {exc}")

        # 提取硬关键词：拼接前 100 条评论文本
        extracted_keywords = []
        if sample_comments_db:
            comment_texts = []
            for item in sample_comments_db[:100]:
                txt = item.get("text") or item.get("body") or ""
                if txt:
                    comment_texts.append(re.sub(r"\[🔗\]\([^)]*\)", "", txt))
            if comment_texts:
                try:
                    kw_res = await extract_keywords("\n".join(comment_texts), max_keywords=15)
                    raw_kw = kw_res.keywords
                    STOPWORDS = {
                        "like", "time", "water", "people", "get", "make", "made", "use",
                        "used", "one", "two", "need", "really", "back", "good", "bad",
                        "day", "now", "take", "well", "year", "month", "week",
                    }
                    extracted_keywords = [k for k in raw_kw if k and k.lower() not in STOPWORDS and len(k) > 2][:15]
                except Exception as exc:
                    print(f"⚠️ comment keyword extraction failed: {exc}")
        if not extracted_keywords and topic_keywords_override:
            extracted_keywords = topic_keywords_override

        # Price sensitivity & usage context are derived from the same文本样本
        combined_texts: list[str] = []
        for item in sample_comments_db or []:
            txt = item.get("text") or item.get("body") or ""
            if txt:
                combined_texts.append(txt[:800])
        for item in top_posts_db or []:
            txt = item.get("title") or item.get("text") or item.get("body") or ""
            if txt:
                combined_texts.append(txt[:800])
        price_analysis = _analyze_price_signals(combined_texts)
        usage_context = _analyze_usage_context(combined_texts, args.topic)

        # Pass topic_tokens to _build_facts
        facts_json_str = _build_facts(
            stats,
            clusters,
            args.topic,
            topic_tokens,
            args.days,
            selected_communities=final_comm,
            need_distribution=need_distribution,  # Phase 5.2
            brand_backfill=brand_backfill,
            market_landscape=market_landscape,
            pain_tree=pain_tree,
            topic_keywords_override=topic_keywords_override or None,
            business_signals=business_signals,
            market_saturation=market_saturation,
            extracted_keywords=extracted_keywords,
            ranked_communities=final_comm,
            price_analysis=price_analysis,
            usage_context=usage_context,
            community_personas=community_personas,
        )
        topic_kw = json.loads(facts_json_str).get("topic_keywords", []) or topic_kw_for_search

# 写入 pain clusters 快照
    clusters_path = base_dir / "reports" / "local-acceptance" / "t1-pain-clusters.json"
    clusters_path.parent.mkdir(parents=True, exist_ok=True)
    clusters_path.write_text(json.dumps(clusters, ensure_ascii=False, indent=2), encoding="utf-8")

    # Re-parse facts_json_str because we need to inject sample_comments_db AND top_posts_db
    facts_dict = json.loads(facts_json_str)
    facts_dict["sample_comments_db"] = sample_comments_db
    facts_dict["top_posts_db"] = top_posts_db  # Injecting the "Flesh"
    
    # --- Hook: meta + lineage + evidence ---
    facts_dict["schema_version"] = "2.0"
    facts_dict["run_id"] = run_id
    facts_dict["snapshot_id"] = snapshot_id
    facts_dict["generated_at"] = datetime.now(timezone.utc).isoformat()
    facts_dict["topic"] = args.topic
    facts_dict["time_window_days"] = args.days
    facts_dict["data_lineage"] = {
        "rule_version": "rulebook_v1",
        "config_hash": config_hash,
        "post_scores_view": "post_scores_latest_v (is_latest=true, rulebook_v1)",
        "comment_scores_view": "comment_scores_latest_v (is_latest=true, rulebook_v1)",
    }
    facts_dict["evidence"] = {
        "quotes": sample_comments_db or []
    }

    # P/S metric package (global)
    total_pain = getattr(stats, "total_pain", None)
    total_sol = getattr(stats, "total_solution", None)
    min_denominator = 1
    ps_value = getattr(stats, "global_ps_ratio", None)
    ps_status = "ok"
    ps_reason = ""
    if total_sol is None or total_pain is None:
        ps_status = "insufficient_sample"
        ps_reason = "no_pain_solution_counts"
    elif (total_sol or 0) < min_denominator:
        ps_status = "insufficient_sample"
        ps_reason = f"solutions<{min_denominator}"
    elif ps_value is None:
        ps_status = "insufficient_sample"
        ps_reason = "ps_ratio_null"
    facts_dict["ps_metric"] = {
        "value": ps_value,
        "numerator": total_pain,
        "denominator": total_sol,
        "min_denominator": min_denominator,
        "status": ps_status,
        "reason": ps_reason,
    }

    # Enrich communities with explainability
    enriched_comm = []
    sorting_notes = []
    for comm in facts_dict.get("communities", []):
        name = comm.get("name") or comm.get("subreddit")
        matched = next((c for c in getattr(stats, "community_stats", []) if getattr(c, "subreddit", "").lower() == str(name).lower()), None)
        ps_num = getattr(matched, "pain_count", None) if matched else None
        ps_den = getattr(matched, "solution_count", None) if matched else None
        pain_density = None
        solution_density = None
        if matched and matched.posts:
            pain_density = round((ps_num or 0) / max(1, matched.posts), 4)
            solution_density = round((ps_den or 0) / max(1, matched.posts), 4)
        ps_status = "ok"
        ps_reason = ""
        if ps_den is None or ps_num is None:
            ps_status = "insufficient_sample"
            ps_reason = "no_pain_solution_counts"
        elif (ps_den or 0) < 1:
            ps_status = "insufficient_sample"
            ps_reason = "solutions<1"
        elif comm.get("pain_density") is None and pain_density is None:
            ps_status = "insufficient_sample"
            ps_reason = "pain_density_null"
        explain = {
            "activity": {
                "posts": getattr(matched, "posts", None),
                "comments": getattr(matched, "comments", None),
                "recent_posts_30d": getattr(matched, "recent_posts_30d", None),
                "recent_comments_30d": getattr(matched, "recent_comments_30d", None),
            },
            "density": {
                "pain_density": pain_density,
                "solution_density": solution_density,
            },
            "ps_metric": {
                "value": getattr(matched, "ps_ratio", None),
                "numerator": ps_num,
                "denominator": ps_den,
                "min_denominator": 1,
                "status": ps_status,
                "reason": ps_reason,
            },
            "sorting_clues": [
                "activity_weighted",
                "ps_ratio_weighted",
                "freshness_30d"
            ],
        }
        # Build human-readable sorting reasons
        if matched:
            sorting_notes.append(
                f"{name}: posts={matched.posts}, comments={matched.comments}, pain/sol={ps_num}/{ps_den}, ps={getattr(matched,'ps_ratio', None)}"
            )
        comm["explain"] = explain
        enriched_comm.append(comm)
    facts_dict["communities"] = enriched_comm
    facts_dict["community_sorting_notes"] = sorting_notes

    # Brand pain enrichment (add gates + evidence)
    brand_pain_entries = facts_dict.get("brand_pain", []) or []
    enriched_brand_pain = []
    min_mentions = 3
    min_authors = 2
    min_evidence = 3
    for b in brand_pain_entries:
        mentions = int(b.get("mentions", 0) or 0)
        authors = int(b.get("unique_authors", 0) or 0)
        evidence_ids = b.get("evidence_comment_ids") or b.get("evidence_quote_ids") or []
        filters_applied = b.get("filters_applied") or ["layer_filter(platform/channel/noise)"]
        status = "ok"
        reason = ""
        if mentions < min_mentions:
            status = "insufficient_sample"
            reason = f"mentions<{min_mentions}"
        elif authors < min_authors:
            status = "insufficient_sample"
            reason = f"unique_authors<{min_authors}"
        elif len(evidence_ids) < min_evidence:
            status = "insufficient_sample"
            reason = f"evidence<{min_evidence}"

        enriched_brand_pain.append(
            {
                **b,
                "unique_authors": authors,
                "filters_applied": filters_applied,
                "evidence_quote_ids": evidence_ids,
                "status": status,
                "min_mentions": min_mentions,
                "min_authors": min_authors,
                "min_evidence": min_evidence,
                "reason": reason,
            }
        )
    facts_dict["brand_pain"] = enriched_brand_pain

    # --- Quality Gate & Metrics ---
    solutions_fallback_used = bool(not top_posts_db and sample_comments_db)

    q_cfg = QUALITY_THRESHOLDS
    comments_min = q_cfg.get("comments_min", 60)
    posts_min = q_cfg.get("posts_min", 30)
    solutions_min = q_cfg.get("solutions_min", 5)
    coverage_min = q_cfg.get("coverage_min", 5)
    if args.mode == "operations":
        solutions_min = min(solutions_min, 3)

    quality = {
        "comments_count": len(sample_comments_db or []),
        "posts_count": len(top_posts_db or []),
        "solutions_count": len(business_signals.get("solutions", []) if business_signals else []),
        "community_coverage": len(core_subs if 'core_subs' in locals() else []),
        "degraded": False,
        "data_fallback": False,
        "posts_fallback": posts_fallback_used if 'posts_fallback_used' in locals() else False,
        "solutions_fallback": solutions_fallback_used,
        "dynamic_blacklist_size": len(dynamic_blacklist),
        "dynamic_whitelist_size": len(dynamic_whitelist),
        "context_relax": context_relax,
        "trend_degraded": trend_degraded if 'trend_degraded' in locals() else False,
    }
    # Fallback triggers
    if quality["comments_count"] < comments_min or quality["posts_count"] < posts_min or manual_data_fallback:
        quality["data_fallback"] = True
    # 不再因 posts_fallback/solutions_fallback 单独触发 data_fallback，保持 info 用途
    # Degraded if thresholds not met
    if (
        quality["comments_count"] < comments_min
        or quality["posts_count"] < posts_min
        or quality["solutions_count"] < solutions_min
        or quality["community_coverage"] < coverage_min
    ):
        quality["degraded"] = True
        print(f"⚠️ Quality degraded: {quality}")

    insufficient_flags: list[str] = []
    if quality["solutions_count"] < solutions_min:
        insufficient_flags.append("solutions_low")
    if quality["comments_count"] < comments_min:
        insufficient_flags.append("comments_low")
    if not (facts_dict.get("price_analysis") or {}).get("price_points"):
        insufficient_flags.append("price_empty")
    if not (facts_dict.get("usage_context") or {}).get("scenarios"):
        insufficient_flags.append("usage_empty")
    if 'trend_degraded' in locals() and trend_degraded:
        insufficient_flags.append("trend_degraded")
    bs = business_signals or {}
    if not any(bs.get(k) for k in ("high_value_pains", "buying_opportunities", "competitor_insights", "solutions")):
        insufficient_flags.append("business_signals_empty")

    # Diagnostics block: coverage + missing flags (Step 1)
    diagnostics = {
        "coverage": {
            "comments": len(sample_comments_db or []),
            "posts": len(top_posts_db or []),
            "solutions": len(bs.get("solutions", []) if bs else []),
            "communities": len(core_subs if "core_subs" in locals() else []),
        },
        "missing_flags": {
            "ps_ratio": facts_dict.get("global_ps_ratio") is None,
            "brand_pain": not bool(facts_dict.get("brand_pain")),
            "quotes": not bool((facts_dict.get("evidence") or {}).get("quotes")),
            "personas": not bool(facts_dict.get("community_personas")),
        },
        "notes": {
            "trend_degraded": trend_degraded if "trend_degraded" in locals() else False,
            "posts_fallback": quality.get("posts_fallback"),
            "solutions_fallback": quality.get("solutions_fallback"),
            "comments_fallback": manual_data_fallback,
        },
    }
    facts_dict["diagnostics"] = diagnostics
    if quality["data_fallback"]:
        insufficient_flags.append("data_fallback")
    if quality["degraded"]:
        insufficient_flags.append("degraded")
    if trend_degraded:
        insufficient_flags.append("trend_degraded")

    # 去重 insufficient_flags，保持顺序
    insufficient_flags = list(dict.fromkeys(insufficient_flags))

    # Confidence (simple heuristic per module + overall)
    def _flag(value: bool) -> float:
        return 1.0 if value else 0.0

    conf_modules = {
        "coverage": _flag(len(sample_comments_db or []) >= 80) * 0.25
        + _flag(len(top_posts_db or []) >= 40) * 0.25,
        "ps": _flag(not diagnostics["missing_flags"]["ps_ratio"]) * 0.25,
        "brand_pain": _flag(any(bp.get("status") == "ok" for bp in facts_dict.get("brand_pain", []))) * 0.25,
        "solutions": _flag(len(business_signals.get("solutions", []) if business_signals else []) >= 5) * 0.25,
    }
    overall_conf = min(1.0, sum(conf_modules.values()))
    facts_dict["confidence"] = {
        "overall": round(overall_conf, 2),
        **{k: round(v, 2) for k, v in conf_modules.items()},
    }

    # v2 package skeleton (non-breaking: keep existing fields, add v2 node)
    meta_start = datetime.now(timezone.utc) - timedelta(days=args.days)
    meta = {
        "topic": args.topic,
        "time_window": {
            "start": meta_start.isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
            "days": args.days,
        },
        "generated_at": facts_dict.get("generated_at"),
        "report_id": run_id,
    }
    data_lineage = {
        "source_range": compute_source_range(
            posts=top_posts_db or [],
            comments=sample_comments_db or [],
        ),
        "labels_version": None,
        "entities_version": None,
        "embeddings_version": None,
        "rule_version": "rulebook_v1",
        "config_hash": config_hash,
        "git_commit": subprocess.getoutput("git rev-parse HEAD").strip() if Path(".git").exists() else None,
    }
    profile_for_v2: TopicProfile | None = active_profile if "active_profile" in locals() else None
    # 窄题可配置门槛（topic profile overrides），默认保持现有宽松口径
    pain_min_mentions = (
        profile_for_v2.pain_min_mentions
        if profile_for_v2 and profile_for_v2.pain_min_mentions is not None
        else 3
    )
    pain_min_unique_authors = (
        profile_for_v2.pain_min_unique_authors
        if profile_for_v2 and profile_for_v2.pain_min_unique_authors is not None
        else 2
    )
    brand_min_mentions = (
        profile_for_v2.brand_min_mentions
        if profile_for_v2 and profile_for_v2.brand_min_mentions is not None
        else 3
    )
    brand_min_unique_authors = (
        profile_for_v2.brand_min_unique_authors
        if profile_for_v2 and profile_for_v2.brand_min_unique_authors is not None
        else 2
    )
    definitions = {
        "ps_metric": {
            "description": "痛点与方案关系指标",
            "min_denominator": 1,
            "smoothing": "laplace_1",
        },
        "pain_cluster_threshold": {
            "min_mentions": int(pain_min_mentions),
            "min_unique_authors": int(pain_min_unique_authors),
            "min_evidence": 1,
        },
        "brand_pain_threshold": {
            "min_mentions": int(brand_min_mentions),
            "min_unique_authors": int(brand_min_unique_authors),
            "min_evidence": 3,
        },
    }
    diagnostics_v2 = {
        "coverage": {
            "comments": len(sample_comments_db or []),
            "posts": len(top_posts_db or []),
            "solutions": len(business_signals.get("solutions", []) if business_signals else []),
            "communities": len(core_subs if "core_subs" in locals() else []),
        },
        "missingness": {
            "quotes_missing_rate": 0.0 if (sample_comments_db or []) else 1.0,
            "ps_insufficient": diagnostics["missing_flags"].get("ps_ratio", False),
        },
    }
    evidence_v2 = {
        "quotes": facts_dict.get("evidence", {}).get("quotes", []),
    }
    communities_v2 = []
    for comm in facts_dict.get("communities", []):
        expl = comm.get("explain", {}) or {}
        communities_v2.append(
            {
                "subreddit": comm.get("name") or comm.get("subreddit"),
                "tier": comm.get("tier"),
                "activity": {
                    "posts_30d": (expl.get("activity") or {}).get("recent_posts_30d"),
                    "comments_30d": (expl.get("activity") or {}).get("recent_comments_30d"),
                },
                "densities": (expl.get("density") or {}),
                "ps_metric": (expl.get("ps_metric") or {}),
                "confidence": facts_dict.get("confidence", {}).get("overall"),
            }
        )

    # --- Phase2: pains / brand_pain / solutions are computed from THIS run's samples ---
    if profile_for_v2:
        pain_th = definitions.get("pain_cluster_threshold", {}) if isinstance(definitions, dict) else {}
        pain_clusters_v2 = compute_pain_clusters_v2(
            posts=top_posts_db or [],
            comments=sample_comments_db or [],
            profile=profile_for_v2,
            max_clusters=5,
            min_mentions=int(pain_th.get("min_mentions", 3) or 3),
            min_unique_authors=int(pain_th.get("min_unique_authors", 2) or 2),
            max_evidence=5,
        )
        # Candidate brands: profile anchors + computed top brands
        brand_candidates: list[str] = []
        brand_candidates.extend(profile_for_v2.required_entities_any or [])
        brand_candidates.extend(profile_for_v2.soft_required_entities_any or [])
        brand_candidates.extend([b for b in (locals().get("top_brands") or []) if isinstance(b, str)])
        bp_th = definitions.get("brand_pain_threshold", {}) if isinstance(definitions, dict) else {}
        brand_pain_v2 = compute_brand_pain_v2(
            posts=top_posts_db or [],
            comments=sample_comments_db or [],
            profile=profile_for_v2,
            pain_clusters=pain_clusters_v2,
            brand_candidates=brand_candidates,
            min_mentions=int(bp_th.get("min_mentions", 3) or 3),
            min_unique_authors=int(bp_th.get("min_unique_authors", 2) or 2),
            min_evidence=int(bp_th.get("min_evidence", 3) or 3),
            max_items=10,
            max_evidence=5,
        )
        solutions_v2 = filter_solutions_by_profile(
            business_signals.get("solutions", []) if business_signals else [],
            profile=profile_for_v2,
            max_items=10,
        )
    else:
        pain_clusters_v2 = []
        brand_pain_v2 = []
        solutions_v2 = business_signals.get("solutions", []) if business_signals else []
    signals_v2 = {
        "communities": communities_v2,
        "pain_clusters": pain_clusters_v2,
        "brand_pain": brand_pain_v2,
    }
    notes = {
        "limitations": insufficient_flags,
        "warnings": diagnostics.get("notes"),
    }
    facts_dict["trend_analysis"] = trend_data
    facts_dict["trend_source"] = trend_source
    facts_dict["trend_time_window_days_used"] = time_window_used
    facts_dict["entity_sentiment"] = entity_sentiment
    facts_dict["pain_hierarchy"] = pain_tree  # 兼容字段名
    facts_dict["pain_tree"] = pain_tree
    facts_dict["brand_sentiment_top"] = brand_sentiment_top
    facts_dict["solutions"] = business_signals.get("solutions", [])
    intent_scores, intent_score_avg = _compute_intent_scores(
        sample_comments_db, top_posts_db, opportunity_scorer
    )
    updated_communities, opportunity_scores = _apply_opportunity_scores(
        facts_dict.get("communities", []),
        intent_scores,
    )
    facts_dict["communities"] = updated_communities
    facts_dict["opportunity_scores"] = opportunity_scores
    facts_dict["intent_scores"] = intent_scores
    facts_dict["intent_score_avg"] = intent_score_avg
    facts_dict["community_personas"] = community_personas
    facts_dict["dynamic_whitelist"] = sorted(list(dynamic_whitelist))
    facts_dict["dynamic_blacklist"] = sorted(list(dynamic_blacklist))
    facts_dict["trend_degraded"] = trend_degraded

    # --- Phase2: aggregates 口径统一到本次样本（top_posts_db + sample_comments_db） ---
    analysis_community_bucket: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"posts": 0, "comments": 0, "unique_authors": set()}
    )
    for p in top_posts_db or []:
        sub = str(p.get("subreddit") or "").lower()
        if not sub:
            continue
        b = analysis_community_bucket[sub]
        b["posts"] += 1
        aid = p.get("author_id")
        if isinstance(aid, str) and aid:
            b["unique_authors"].add(aid)
    for c in sample_comments_db or []:
        sub = str(c.get("subreddit") or "").lower()
        if not sub:
            continue
        b = analysis_community_bucket[sub]
        b["comments"] += 1
        aid = c.get("author_id")
        if isinstance(aid, str) and aid:
            b["unique_authors"].add(aid)
    analysis_communities = [
        {
            "subreddit": sub,
            "posts": int(b["posts"]),
            "comments": int(b["comments"]),
            "unique_authors": len(b["unique_authors"]),
        }
        for sub, b in analysis_community_bucket.items()
    ]
    analysis_communities.sort(key=lambda x: (x["comments"], x["posts"]), reverse=True)

    def _to_month(ts: Any) -> str | None:
        if isinstance(ts, str) and ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                return None
            return f"{dt.year:04d}-{dt.month:02d}"
        return None

    month_counts: dict[str, int] = defaultdict(int)
    for p in top_posts_db or []:
        m = _to_month(p.get("created_at"))
        if m:
            month_counts[m] += 1
    for c in sample_comments_db or []:
        m = _to_month(c.get("created_at"))
        if m:
            month_counts[m] += 1
    analysis_trend = [{"month": k, "count": v} for k, v in sorted(month_counts.items())]
    print(f"👥 Final communities (top 10): {[c.get('name') for c in facts_dict.get('communities', [])[:10]]}")
    if dynamic_whitelist:
        print(f"✅ Dynamic whitelist ({len(dynamic_whitelist)}): {sorted(list(dynamic_whitelist))[:10]}")
    if dynamic_blacklist:
        print(f"🚧 Dynamic blacklist ({len(dynamic_blacklist)}): {sorted(list(dynamic_blacklist))[:10]}")

    # --- Single facts_v2 package ---
    aggregates_block = {
        "communities": analysis_communities,
        "trend_analysis": analysis_trend,
        "trend_source": "analysis_sample",
        "trend_time_window_days_used": args.days,
        "entity_sentiment": entity_sentiment,
        "brand_sentiment_top": brand_sentiment_top,
        "solutions": solutions_v2 or [],
        "intent_scores": intent_scores,
        "intent_score_avg": intent_score_avg,
        "opportunity_scores": opportunity_scores,
        "dynamic_whitelist": sorted(list(dynamic_whitelist)),
        "dynamic_blacklist": sorted(list(dynamic_blacklist)),
        "trend_degraded": trend_degraded,
    }
    business_signals_block = {
        "high_value_pains": pain_clusters_v2,
        "brand_pain": brand_pain_v2,
        "competitor_insights": facts_dict.get("competitor_insights"),
        "market_saturation": facts_dict.get("market_saturation"),
        "solutions": solutions_v2 or [],
    }
    facts_v2_package = {
        "schema_version": "2.0",
        "meta": meta,
        "data_lineage": data_lineage,
        "definitions": definitions,
        "aggregates": aggregates_block,
        "business_signals": business_signals_block,
        "pain_tree": pain_tree,
        "pain_clusters": pain_clusters_v2,
        "sample_comments_db": sample_comments_db,
        "sample_posts_db": top_posts_db,
        "diagnostics": diagnostics_v2,
        "evidence": evidence_v2,
        "signals": signals_v2,
        "confidence": facts_dict.get("confidence"),
        "notes": notes,
    }
    facts_v2_package = _convert_decimals_to_floats(facts_v2_package)

    # --- Phase3: 质量闸门（不达标就不进报告阶段） ---
    quality_result = quality_check_facts_v2(
        facts_v2_package,
        profile=active_profile if "active_profile" in locals() else None,
    )
    # 写回 facts_v2，方便后续排查
    diagnostics_node = facts_v2_package.get("diagnostics") or {}
    if isinstance(diagnostics_node, dict):
        diagnostics_node["quality_gate"] = {
            "passed": quality_result.passed,
            "tier": quality_result.tier,
            "flags": quality_result.flags,
            "metrics": quality_result.metrics,
        }
        facts_v2_package["diagnostics"] = diagnostics_node
    notes_node = facts_v2_package.get("notes") or {}
    if isinstance(notes_node, dict):
        limitations = notes_node.get("limitations") or []
        if isinstance(limitations, list):
            merged = list(dict.fromkeys([*limitations, *quality_result.flags]))
            notes_node["limitations"] = merged
        facts_v2_package["notes"] = notes_node

    out_dir = base_dir / "reports" / "local-acceptance"
    out_dir.mkdir(parents=True, exist_ok=True)
    facts_out_path = out_dir / f"facts_v2_{run_id}.json"
    facts_out_path.write_text(json.dumps(facts_v2_package, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Single facts_v2 package exported: {facts_out_path}")

    # Optional: run validator on v2 (best effort, non-blocking)
    try:
        res = subprocess.run(
            ["python", "scripts/validate_facts_v2.py", str(facts_out_path)],
            cwd=base_dir.parent,
            capture_output=True,
            text=True,
        )
        if res.stdout:
            print(res.stdout.strip())
        if res.returncode != 0 and res.stderr:
            print(res.stderr.strip())
    except Exception as exc:
        print(f"⚠️ Validator skipped: {exc}")

    await _write_quality_audit(
        session,
        run_id=run_id,
        args=args,
        config_hash=config_hash,
        time_window_used=time_window_used,
        trend_source=trend_source,
        trend_degraded=trend_degraded,
        quality=quality,
        insufficient_flags=insufficient_flags,
        dynamic_whitelist=dynamic_whitelist,
        dynamic_blacklist=dynamic_blacklist,
    )

    # In-memory slice for LLM/Admin
    facts_for_llm = json.dumps(
        build_facts_slice_for_report(facts_v2_package),
        ensure_ascii=False,
        indent=2,
    )
    print(f"✂️  Facts slice (in-memory) size: {len(facts_for_llm)} chars")
    
    if args.skip_llm:
        print("🛑 Skip LLM stage (--skip-llm). Single facts_v2 已生成。")
        return

    if quality_result.tier == "X_blocked":
        print(f"🛑 Quality gate blocked report generation: {quality_result.flags}")
        return

    # --- 2-Stage Generation ---
    # print(f"🚧 SKIPPING LLM GENERATION to save tokens. Check {facts_debug_path} for accuracy.")
    # return

    full_report = ""
    if quality_result.tier == "C_scouting":
        print(f"🤖 Calling LLM Scouting Brief ({args.model})...")
        prompt = _make_prompt_scouting_brief(args.topic, args.product_desc, facts_for_llm)
        part = await _llm_generate(prompt, model=args.model)
        if not part or not part.strip():
            raise ValueError("LLM returned empty response for Scouting Brief.")
        full_report = part
    else:
        print(f"🤖 Calling LLM Stage 1/2 ({args.model})...")
        prompt1 = _make_prompt_part1(args.topic, args.product_desc, facts_for_llm)
        part1 = await _llm_generate(prompt1, model=args.model)
        if not part1 or not part1.strip():
            raise ValueError("LLM returned empty response for Part 1.")

        print(f"🤖 Calling LLM Stage 2/2 ({args.model})...")
        if quality_result.tier == "B_trimmed":
            prompt2 = _make_prompt_part2_trimmed(args.topic, args.product_desc, facts_for_llm)
        else:
            prompt2 = _make_prompt_part2(args.topic, args.product_desc, facts_for_llm)
        part2 = await _llm_generate(prompt2, model=args.model)
        if not part2 or not part2.strip():
            raise ValueError("LLM returned empty response for Part 2.")

        # Combine
        full_report = f"{part1}\n\n---\n\n{part2}"

    report_path = base_dir / args.out
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(full_report, encoding="utf-8")
    
    print(f"✅ Stats snapshot: {stats_path}")
    print(f"✅ Clusters snapshot: {clusters_path}")
    print(f"✅ Report generated: {report_path} (LLM Success, 2 Stages)")
    if quality_result.tier != "C_scouting":
        recommended_keywords = _extract_recommended_keywords(full_report, topic_kw)
        inserted = await _insert_semantic_candidates(recommended_keywords)
        if inserted:
            print(f"✅ semantic_candidates inserted/kept pending: {inserted}")
    if args.run_quality:
        try:
            print("➡️  Running stage4-quality ...")
            subprocess.run(["make", "stage4-quality"], check=False, cwd=base_dir.parent)
        except Exception as exc:  # pragma: no cover
            print(f"⚠️ stage4-quality 执行异常：{exc}")


if __name__ == "__main__":
    asyncio.run(main())
