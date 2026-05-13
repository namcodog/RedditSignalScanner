from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any, Mapping

import yaml

from app.services.hotpost.card_content_llm_router import build_card_content_client


MIN_EFFECTIVE_SAMPLE = 12
CONTROVERSY_LLM_MODEL = "google/gemini-2.5-flash-lite"
LLM_SUMMARY_VERSION = "cn_human_point_slots_v8"
_LLM_TIMEOUT_SECONDS = 20.0
_PROMPT_COMMENT_LIMIT = 24
_HOTPOST_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "hotpost_quality.yaml"


@lru_cache(maxsize=1)
def load_hot_controversy_llm_config() -> dict[str, Any]:
    payload = yaml.safe_load(_HOTPOST_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    raw = payload.get("hot_controversy") or {}
    if not isinstance(raw, dict):
        raise ValueError("hotpost_quality.yaml hot_controversy is invalid")
    model = str(raw.get("model") or CONTROVERSY_LLM_MODEL).strip()
    summary_version = str(raw.get("summary_version") or LLM_SUMMARY_VERSION).strip()
    timeout_seconds = float(raw.get("timeout_seconds") or _LLM_TIMEOUT_SECONDS)
    if not model or not summary_version:
        raise ValueError("hotpost_quality.yaml hot_controversy missing model or summary_version")
    return {
        "model": model,
        "summary_version": summary_version,
        "timeout_seconds": timeout_seconds,
    }


async def build_hot_controversy_result(
    *,
    card: Mapping[str, Any],
    sample: Mapping[str, Any],
    llm_client:Optional[ Any] = None,
    llm_model:Optional[ str] = None,
) ->Optional[ tuple[dict[str, Any]], dict[str, Any]]:
    _ = llm_model
    config = load_hot_controversy_llm_config()
    model_name = str(config["model"])
    meta = {
        "post_id": sample.get("post_id"),
        "sample_size": int(sample.get("sample_size") or 0),
        "sampled_at": sample.get("sampled_at"),
        "fetch_status": str(sample.get("fetch_status") or "unknown"),
        "llm_summary_version": str(config["summary_version"]),
        "sample_quality": _sample_quality(int(sample.get("sample_size") or 0)),
        "summary_status": "skipped",
    }
    if meta["fetch_status"] != "ok" or meta["sample_size"] <= 0:
        return None, meta | {"summary_status": "no_sample"}

    client = llm_client or build_card_content_client(model_name, timeout=float(config["timeout_seconds"]))
    try:
        raw = await client.generate(
            _render_prompt(card=card, sample_comments=list(sample.get("sample_comments") or [])),
            response_format={"type": "json_object", "schema": _response_schema()},
            temperature=0.1,
            max_tokens=600,
        )
    except Exception:
        return None, meta | {"summary_status": "llm_failed"}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, meta | {"summary_status": "invalid_json"}

    support_count = _nonnegative_int(payload.get("support_comments"))
    oppose_count = _nonnegative_int(payload.get("oppose_comments"))
    neutral_count = _nonnegative_int(payload.get("neutral_comments"))
    total = support_count + oppose_count + neutral_count
    if total <= 0:
        return None, meta | {"summary_status": "empty_counts"}

    support_point = _normalize_cn_output(_clean_line(payload.get("support_point")))
    oppose_point = _normalize_cn_output(_clean_line(payload.get("oppose_point")))
    neutral_point = _normalize_cn_output(_clean_line(payload.get("neutral_point")))
    debate_focus = _normalize_cn_output(_clean_line(payload.get("debate_focus")))

    chart = _build_chart(
        support_count=support_count,
        oppose_count=oppose_count,
        neutral_count=neutral_count,
        support_point=support_point,
        oppose_point=oppose_point,
        neutral_point=neutral_point,
        debate_focus=debate_focus,
        confidence=_confidence(sample_size=meta["sample_size"]),
    )
    return chart, meta | {"summary_status": "ok", "confidence_reason": _clean_line(payload.get("confidence_reason"))}


def _build_chart(
    *,
    support_count: int,
    oppose_count: int,
    neutral_count: int,
    support_point: str,
    oppose_point: str,
    neutral_point: str,
    debate_focus: str,
    confidence: str,
) -> dict[str, Any]:
    total = support_count + oppose_count + neutral_count
    support_ratio = round(support_count / total, 2)
    oppose_ratio = round(oppose_count / total, 2)
    neutral_ratio = round(max(0.0, 1.0 - support_ratio - oppose_ratio), 2)
    dominant_side = max(
        (
            ("support", support_ratio),
            ("oppose", oppose_ratio),
            ("neutral", neutral_ratio),
        ),
        key=lambda item: item[1],
    )[0]
    return {
        "support_ratio": support_ratio,
        "oppose_ratio": oppose_ratio,
        "neutral_ratio": neutral_ratio,
        "support_point": support_point,
        "oppose_point": oppose_point,
        "neutral_point": neutral_point,
        "debate_focus": debate_focus,
        "dominant_side": dominant_side,
        "confidence": confidence,
    }


def _render_prompt(*, card: Mapping[str, Any], sample_comments: list[dict[str, Any]]) -> str:
    trimmed = sample_comments[:_PROMPT_COMMENT_LIMIT]
    comments_blob = json.dumps(trimmed, ensure_ascii=False, indent=2)
    title = str(card.get("title") or "")
    summary_line = str(card.get("summary_line") or "")
    return (
        "你是小程序首页的爆贴争议压缩器。任务不是写长文，而是把评论样本压成真人读完后的争议结构。\n"
        "必须只基于给出的评论样本判断，不要脑补，不要引用卡片外信息。\n"
        "输出一个 JSON 对象，字段必须完整：\n"
        "support_comments, oppose_comments, neutral_comments,\n"
        "support_point, oppose_point, neutral_point, debate_focus, confidence_reason。\n"
        "要求：\n"
        "1. 三类 comment 计数必须是整数，且代表真实样本判断，不要模板桶位。\n"
        "2. 所有输出必须是中文，不要夹英文单词、英文字母、代码、产品缩写或原文摘抄。\n"
        "3. 像 AI、Meta、GPT、Claude 这类英文名，统一改成中文替代说法，比如“人工智能”“平台”“头部模型”“这套工具”。\n"
        "4. debate_focus 必须是一句 18 到 28 个中文字符的冲突短句，而且必须包含“还是/到底/该不该/要不要/是不是”之一。\n"
        "5. support_point / oppose_point / neutral_point 都必须是 8 到 16 个中文字，像评论原话压缩，不像分析报告，不要写成长解释。\n"
        "6. 三句都不能为空。就算某一边很弱，也要从样本里挑出最具体的一条质疑，不能留空。\n"
        "7. support_point 要写成一句站队的话，像“先把量做起来，再慢慢补质量”。\n"
        "8. oppose_point 要写成一句反驳的话，像“跑分好看，不等于真能用”。\n"
        "9. neutral_point 只能写不站队的人具体在等什么、卡在哪、怕什么，句式优先用“先看X”“还得看X”“主要卡在X”。\n"
        "10. neutral_point 禁止出现“评论区”“大家在讨论”“用户”“大家在等”“还在观望”“还在观察”。\n"
        "11. support_point / oppose_point / neutral_point 都不要出现“说明/体现/反映/表明/意味着”。\n"
        "12. 没有明显对立时，计数要保守，不要轻易打满。\n"
        "13. 样本少时优先保守，不要把任何一方写成压倒性多数，也不要用高比例中性装稳定。\n"
        "14. 输出前自检：不能有任何英文字母；focus 必须带冲突标记；三句都不能为空；neutral 必须具体到一个等待点、卡点或风险点。\n"
        "坏例子：大家在讨论插件兼容性。\n"
        "好例子：先看能不能少手动维护。\n"
        "坏例子：模型运行需要大量硬件资源，普通用户难以负担。\n"
        "好例子：先看本地机器扛不扛得住。\n\n"
        f"卡片标题：{title}\n"
        f"卡片摘要：{summary_line}\n"
        f"评论样本（共 {len(trimmed)} 条）：\n{comments_blob}\n"
    )


def _response_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "support_comments": {"type": "INTEGER"},
            "oppose_comments": {"type": "INTEGER"},
            "neutral_comments": {"type": "INTEGER"},
            "support_point": {"type": "STRING"},
            "oppose_point": {"type": "STRING"},
            "neutral_point": {"type": "STRING"},
            "debate_focus": {"type": "STRING"},
            "confidence_reason": {"type": "STRING"},
        },
        "required": [
            "support_comments",
            "oppose_comments",
            "neutral_comments",
            "support_point",
            "oppose_point",
            "neutral_point",
            "debate_focus",
            "confidence_reason",
        ],
    }


def _sample_quality(sample_size: int) -> str:
    if sample_size >= 30:
        return "high"
    if sample_size >= 20:
        return "medium"
    return "low"


def _confidence(*, sample_size: int) -> str:
    if sample_size < MIN_EFFECTIVE_SAMPLE:
        return "low"
    if sample_size >= 30:
        return "high"
    return "medium"


def _nonnegative_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _clean_line(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def _normalize_cn_output(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "ChatGPT": "对话产品",
        "Gemini": "对话产品",
        "GPT-4o": "头部模型",
        "GPT": "模型",
        "Claude": "模型",
        "Anthropic": "平台",
        "Meta": "平台",
        "AI": "人工智能",
        "RAG": "检索方案",
        "winback discount": "挽回优惠",
        "discount": "优惠",
        "winback": "挽回",
    }
    normalized = text
    for needle, repl in replacements.items():
        normalized = normalized.replace(needle, repl)
    normalized = (
        normalized.replace("大家在等", "先看")
        .replace("还在观望", "先看")
        .replace("还在观察", "先看")
    )
    normalized = re.sub(r"[.…]{2,}", "", normalized)
    normalized = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", normalized)
    return _clean_line(normalized)


__all__ = [
    "CONTROVERSY_LLM_MODEL",
    "MIN_EFFECTIVE_SAMPLE",
    "LLM_SUMMARY_VERSION",
    "build_hot_controversy_result",
    "load_hot_controversy_llm_config",
]
