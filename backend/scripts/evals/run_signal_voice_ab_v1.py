"""Signal readout A/B comparison – voice quality before/after.

Usage:
    python backend/scripts/evals/run_signal_voice_ab_v1.py --limit 3

Picks published validate cards as ground-truth input, regenerates them with
(A) current prompt and (B) candidate prompt, then prints side-by-side.
No production data is changed – purely read-only comparison.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

# Load API keys before importing app modules
from dotenv import load_dotenv  # noqa: E402
load_dotenv(BACKEND_ROOT / ".env")

from app.services.hotpost.card_content_generator import (
    _all_banned_patterns,
    _generate_json,
    _apply_signal_content,
    load_card_content_models,
    load_card_content_rules,
)
from app.services.hotpost.card_content_llm_router import (
    build_card_content_client,
    resolve_card_content_model_route,
)
from app.services.hotpost.card_content_prompts import build_signal_prompt
from app.services.hotpost.reddit_guide_prompt_assets import build_reddit_guide_prompt_prefix
from app.services.hotpost.semantic_readout import (
    finalize_signal_readout,
    semantic_prompt_extra,
)
from app.services.hotpost.signal_skill_experiment import build_eval_signal_draft
from app.schemas.hotpost_card_drafts import QuotePreview, ValidationCardDraft, ValidationDetail


EVALS_DIR = BACKEND_ROOT / "scripts" / "evals"


# ── Candidate prompt (the "B" variant) ──────────────────────────────────
def build_signal_prompt_candidate(
    draft: ValidationCardDraft,
    *,
    banned_patterns: list[str],
) -> list[dict[str, str]]:
    """Candidate prompt: stronger voice instructions for summary_line + detail fields."""
    system = (
        build_reddit_guide_prompt_prefix(mode_name="潜力快帖")
        + "\n"
        "你现在是在把一条值得看的 Reddit 讨论转给朋友。"
        "只能基于输入证据写卡，不得脑补，不得补行业常识。输出必须是合法 JSON。"
        "这是一张『信号卡』：先说眼前冒出来的症状，再说为什么值得继续追，不给空话，不装结论。"
        "title 写成中文症状句，15-30 字。"

        # ── summary_line: 核心改动 ──
        "summary_line 是一句带判断的事实浓缩：用一句话说清楚'这帖真正在吵什么'，嵌入一句原话翻译当锚点。"
        "不要罗列两方观点，不要写成'有人觉得A，也有人觉得B'。"
        "好的 summary_line：'大家已经掰着指头算 Cursor 每月值不值了——快是快，但不少用户宁愿用回慢版本。'"
        "坏的 summary_line：'有人觉得好，也有人觉得不好，双方各执一词。'"

        "不要写'正确的废话'。即使观点正确，只要普通用户一眼就知道、读完没有新增判断，也算失败。"
        "audience 不是目标受众，而是 Reddit 上谁在聊这件事，要具体到人群和场景。"
        "audience 只写成一个自然的人群短语，不要写成整句，不要出现 subreddit 名、帖子、评论区、讨论、吐槽、分享帖这些词。"
        "好的 audience 像『会后总要追行动项归属的经理和项目负责人』『在企业里评估 AI 工具合规和落地风险的人』。"
        "why_now 会由系统根据结构化信号重写，所以你不用在输出里夹带规则名、温度词或内部标签。"
        "不要输出 switch_signal_7d、recurring_7d、new_threads_24h、signal_level、rising、hot、sustained 这些内部词。"
        "客户端默认不直接展示后台字段、广告后台黑话、工程内部术语。"
        "像 primary goal、offline conversion、imported conversions、tool calling、silent failure、click fraud 这类词，必须翻成用户一眼能懂的人话。"
        "客户端文案默认不用泛泛的'人'做主语，优先明确写成'用户'。"
        "客户端文案默认不用'脑子'这类口语词，统一改成'思考'或更具体的动作。"
        "如果非要提专业概念，也要先写业务后果，再补这个概念，不能把后台词直接端给用户。"
        "summary_line、why_now、detail 里都不要写那种'大家都知道这是对的'的常识句，必须把判断往前推。"

        # ── detail 字段: 核心改动 ──
        "pain_point 写成一句话，不做平衡阐述，直接说这群人到底被什么卡住了。"
        "好的 pain_point：'付钱为速度，还是为效果？很多人已经算不过来了。'"
        "target_user_and_scene 不要像 persona 画像，写成一个具体的人在一个具体的场景。"
        "好的 target_user_and_scene：'写代码天天靠 AI、月底要比价的开发者。'"
        "why_test_now 前半句用原话锚定，后半句给你的判断。不要用'说明…开始…从…回到…'这类分析谓语。"
        "continue_signal 写成和这个具体话题相关的判断句，不要写'如果更多社区出现同样抱怨'这种万能句。"
        "stop_signal 也要绑定当前话题的具体场景，不要泛泛说'如果只剩零散吐槽'。"

        "preview_quote_permalink 必须从给定 evidence_quotes 里选择。"
        "禁止使用这些套话："
        + " / ".join(banned_patterns)
    )
    evidence = [
        {
            "text": quote.text,
            "community": quote.community,
            "permalink": quote.permalink,
        }
        for quote in draft.evidence_quotes
    ]
    user = {
        "card_type_requested": draft.card_type,
        "source_scope_id": draft.source_scope_id,
        "source_scope_name": draft.source_scope_name,
        "matched_subreddit": draft.matched_subreddit,
        "source_communities": draft.source_communities,
        "thread_count": draft.thread_count,
        "community_count": draft.community_count,
        "quote_count": draft.quote_count,
        "intent_tags": draft.intent_tags,
        "signal_level": draft.signal_level,
        "why_now_reason": draft.why_now_reason,
        "current_title": draft.title,
        "source_link": draft.source_link,
        "evidence_quotes": evidence,
        "output_schema": {
            "title": "string",
            "summary_line": "string",
            "audience": "string",
            "why_now": "string",
            "preview_quote_permalink": "string",
            "detail": {
                "pain_point": "string",
                "target_user_and_scene": "string",
                "why_test_now": "string",
                "continue_signal": "string",
                "stop_signal": "string",
            },
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, indent=2)},
    ]


def _load_published_signal_cards(limit: int) -> list[dict[str, Any]]:
    """Load validate cards from the latest release as input bundles."""
    releases_dir = BACKEND_ROOT / "data" / "hotpost" / "releases"
    latest_path = releases_dir / "latest.json"
    if not latest_path.exists():
        raise FileNotFoundError("No latest.json found")
    release_id = json.loads(latest_path.read_text(encoding="utf-8"))["release_id"]
    cards_dir = releases_dir / release_id / "cards"
    results: list[dict[str, Any]] = []
    for card_path in sorted(cards_dir.glob("*.json")):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        if card.get("card_type") != "validate":
            continue
        if card.get("lane") == "hot":
            continue
        results.append(card)
        if limit and len(results) >= limit:
            break
    return results


def _card_to_eval_draft(card: dict[str, Any]) -> ValidationCardDraft:
    """Reconstruct a ValidationCardDraft from a published card."""
    quotes = [
        QuotePreview(
            text=q["text"],
            community=q.get("community", ""),
            permalink=q.get("permalink", ""),
        )
        for q in card.get("quotes", [])
    ]
    sm = card.get("source_module") or {}
    communities = [str(c) for c in sm.get("primary_communities", [])]
    return ValidationCardDraft(
        draft_id=f"ab-{card['card_id']}",
        candidate_id=card["card_id"],
        candidate_ids=[card["card_id"]],
        card_id=f"ab-{card['card_id']}",
        signal_id=card.get("signal_id", card["card_id"]),
        card_type="validate",
        category_id="validate",
        topic_pack_id=None,
        title=card.get("title", ""),
        source_scope_id=card.get("source_scope_id", ""),
        source_scope_name=card.get("source_scope_name", ""),
        matched_subreddit=card.get("top_community", "").replace("r/", "", 1),
        post_id=card["card_id"],
        source_event_at=None,
        score=0,
        num_comments=0,
        time_window="7d",
        signal_level=card.get("signal_level", "sustained"),
        why_now_reason=card.get("why_now_reason", ""),
        thread_count=int(card.get("thread_count", 1)),
        community_count=int(card.get("community_count", 1)),
        quote_count=len(quotes),
        intent_tags=[str(t) for t in card.get("intent_tags", [])],
        evidence_quotes=quotes,
        summary_line="",
        audience="",
        why_now="",
        source_link=card.get("source_link", ""),
        source_links=[card.get("source_link", "")] if card.get("source_link") else [],
        source_communities=communities,
        draft_status="draft",
        draft_note="ab comparison",
        detail=ValidationDetail(
            pain_point="待生成",
            target_user_and_scene="待生成",
            why_test_now="待生成",
            continue_signal="待生成",
            stop_signal="待生成",
        ),
    )


def _extract_ab_fields(card_draft: ValidationCardDraft) -> dict[str, str]:
    """Extract the key text fields for comparison."""
    return {
        "title": card_draft.title,
        "summary_line": card_draft.summary_line,
        "audience": card_draft.audience,
        "pain_point": card_draft.detail.pain_point,
        "target_user_and_scene": card_draft.detail.target_user_and_scene,
        "why_test_now": card_draft.detail.why_test_now,
        "continue_signal": card_draft.detail.continue_signal,
        "stop_signal": card_draft.detail.stop_signal,
    }


def _print_comparison(
    card_id: str,
    published: dict[str, str],
    baseline: dict[str, str],
    candidate: dict[str, str],
) -> None:
    """Print side-by-side comparison."""
    fields = [
        "title", "summary_line", "audience",
        "pain_point", "target_user_and_scene", "why_test_now",
        "continue_signal", "stop_signal",
    ]
    print(f"\n{'='*80}")
    print(f"  Card: {card_id}")
    print(f"{'='*80}")
    for field in fields:
        pub = published.get(field, "")
        base = baseline.get(field, "")
        cand = candidate.get(field, "")
        print(f"\n  ── {field} ──")
        print(f"  📦 已发布: {pub}")
        print(f"  🅰️ Baseline: {base}")
        print(f"  🅱️ Candidate: {cand}")
    print()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Signal voice A/B comparison")
    parser.add_argument("--limit", type=int, default=3, help="Number of cards to compare")
    args = parser.parse_args()

    cards = _load_published_signal_cards(args.limit)
    if not cards:
        print("No validate cards found in latest release")
        return

    rules = load_card_content_rules()
    models = load_card_content_models()
    banned = _all_banned_patterns(rules)
    client = lambda model, timeout: build_card_content_client(model, timeout=timeout)
    signal_model, signal_timeout = resolve_card_content_model_route(
        models=models,
        topic_pack_id=None,
        lane="signal",
        default_timeout=float(rules["timeouts"]["signal_seconds"]),
    )

    results: list[dict[str, Any]] = []

    for card in cards:
        card_id = card["card_id"]
        print(f"\nProcessing {card_id}...", flush=True)
        draft = _card_to_eval_draft(card)

        # Published version fields
        published_fields = {
            "title": card.get("title", ""),
            "summary_line": card.get("summary_line", ""),
            "audience": card.get("audience", ""),
            "pain_point": (card.get("detail") or {}).get("pain_point", ""),
            "target_user_and_scene": (card.get("detail") or {}).get("target_user_and_scene", ""),
            "why_test_now": (card.get("detail") or {}).get("why_test_now", ""),
            "continue_signal": (card.get("detail") or {}).get("continue_signal", ""),
            "stop_signal": (card.get("detail") or {}).get("stop_signal", ""),
        }

        # (A) Baseline: current prompt
        baseline_msgs = build_signal_prompt(
            draft, banned_patterns=banned,
        )
        extra = semantic_prompt_extra(rules=rules, lane="signal", topic_pack_id=None)
        if extra:
            baseline_msgs[0] = {**baseline_msgs[0], "content": baseline_msgs[0]["content"] + extra}

        baseline_payload = await _generate_json(
            model=signal_model, timeout=signal_timeout,
            messages=baseline_msgs, client_factory=client,
        )
        baseline_draft = _apply_signal_content(draft, baseline_payload, rules)
        baseline_draft = finalize_signal_readout(baseline_draft, source_draft=draft, rules=rules)
        baseline_fields = _extract_ab_fields(baseline_draft)

        # (B) Candidate: optimized prompt
        candidate_msgs = build_signal_prompt_candidate(
            draft, banned_patterns=banned,
        )
        if extra:
            candidate_msgs[0] = {**candidate_msgs[0], "content": candidate_msgs[0]["content"] + extra}

        candidate_payload = await _generate_json(
            model=signal_model, timeout=signal_timeout,
            messages=candidate_msgs, client_factory=client,
        )
        candidate_draft = _apply_signal_content(draft, candidate_payload, rules)
        candidate_draft = finalize_signal_readout(candidate_draft, source_draft=draft, rules=rules)
        candidate_fields = _extract_ab_fields(candidate_draft)

        _print_comparison(card_id, published_fields, baseline_fields, candidate_fields)

        results.append({
            "card_id": card_id,
            "published": published_fields,
            "baseline": baseline_fields,
            "candidate": candidate_fields,
        })

    # Write results
    output_path = EVALS_DIR / "signal_voice_ab_v1_results.json"
    output_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
