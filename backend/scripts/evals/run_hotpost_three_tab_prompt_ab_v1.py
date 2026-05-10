"""Three-tab Hotpost prompt A/B comparison.

This is a read-only experiment runner. It samples published cards from the
latest release, regenerates each card with the current prompt and with a small
plain-language overlay, then writes side-by-side results for review.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
REPORTS_EVALS_DIR = ROOT / "reports" / "evals"
RELEASES_DIR = BACKEND_ROOT / "data" / "hotpost" / "releases"
LANE_ORDER = ("signal", "hot", "breakdown")

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _is_placeholder(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return not normalized or normalized.startswith("your_") or "example" in normalized or normalized == "replace_me"


PROJECT_ENV_OVERRIDE_KEYS = {
    "OPENAI_BASE",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "GEMINI_API_KEY",
    "HOTPOST_FAST_MODEL",
    "HOTPOST_REASONING_MODEL",
    "HOTPOST_REASONING_ENABLED",
}


def load_project_env(env_path: Path = BACKEND_ROOT / ".env", environ: dict[str, str] | None = None) -> None:
    target_environ = os.environ if environ is None else environ
    for key, value in dotenv_values(env_path).items():
        if value is None:
            continue
        current_value = target_environ.get(key)
        if key in PROJECT_ENV_OVERRIDE_KEYS or _is_placeholder(current_value):
            target_environ[key] = str(value)


load_project_env()

from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft  # noqa: E402
from app.schemas.hotpost_clues import QuotePreview, WritingDetail  # noqa: E402
from app.schemas.hotpost_validate_details import build_validation_detail  # noqa: E402
from app.services.hotpost.card_content_generator import (  # noqa: E402
    _all_banned_patterns,
    _apply_breakdown_content,
    _apply_validation_content,
    _breakdown_json_schema,
    _card_content_json_schema_for_draft,
    _generate_json,
    _max_tokens,
    load_card_content_models,
    load_card_content_rules,
)
from app.services.hotpost.card_content_llm_router import (  # noqa: E402
    build_card_content_client,
    resolve_card_content_model_route,
)
from app.services.hotpost.card_content_prompts import (  # noqa: E402
    build_breakdown_prompt,
    build_hot_prompt,
    build_signal_prompt,
)
from app.services.hotpost.semantic_readout import (  # noqa: E402
    finalize_validation_readout,
    semantic_prompt_extra,
)


def load_sample_cards(*, releases_dir: Path = RELEASES_DIR, limit_per_lane: int = 5) -> dict[str, list[dict[str, Any]]]:
    latest_path = releases_dir / "latest.json"
    if not latest_path.exists():
        raise FileNotFoundError(f"Missing latest release pointer: {latest_path}")
    release_id = json.loads(latest_path.read_text(encoding="utf-8"))["release_id"]
    cards_dir = releases_dir / release_id / "cards"
    if not cards_dir.exists():
        raise FileNotFoundError(f"Missing latest release cards directory: {cards_dir}")

    samples: dict[str, list[dict[str, Any]]] = {lane: [] for lane in LANE_ORDER}
    for card_path in sorted(cards_dir.glob("*.json")):
        card = json.loads(card_path.read_text(encoding="utf-8"))
        lane = str(card.get("lane") or "").strip()
        card_type = str(card.get("card_type") or "").strip()
        if lane == "breakdown" and card_type != "write":
            continue
        if lane in {"signal", "hot"} and card_type != "validate":
            continue
        if lane not in samples or len(samples[lane]) >= limit_per_lane:
            continue
        samples[lane].append(card)
        if all(len(rows) >= limit_per_lane for rows in samples.values()):
            break
    return samples


def build_plain_language_overlay() -> str:
    return """

## 本轮 A/B 变体：普通用户可读性

不新增字段，不改字段名，不改 JSON 结构。只改变写法。

- 默认读者不懂 Reddit、不懂广告后台、不懂 AI 工程黑话，也要一眼明白这张卡在说什么。
- 先把英文黑话和后台词翻成用户能感到的动作、成本、风险或取舍；必要时只保留一个很短的英文锚点。
- 不写报告腔，不写行业周报腔，不用“大趋势 / 生态 / 赛道 / 本质 / 值得关注”撑句子。
- 每个字段只说自己的事：title 讲变化或火点，summary_line 讲核心判断，why_now 讲现在为什么值得看，why_test_now 讲哪条证据撑住判断。
- 少写抽象判断，多写谁在什么场景下被什么卡住、开始先看什么、不再先相信什么。
- 如果证据只支持“有人开始这么看”，就写“有用户开始这么看”，不要放大成市场或行业共识。
- 中文要像懂行的人转给朋友，不像咨询报告。
""".strip()


def _with_overlay(messages: list[dict[str, str]], *, enabled: bool) -> list[dict[str, str]]:
    if not enabled:
        return messages
    return [{**messages[0], "content": messages[0]["content"] + "\n\n" + build_plain_language_overlay()}, *messages[1:]]


def _with_retry_instruction(messages: list[dict[str, str]], error: Exception) -> list[dict[str, str]]:
    retry_note = (
        "\n\n## 重写要求\n"
        f"上一次输出没有通过字段校验：{type(error).__name__}: {error}\n"
        "- 不要出现报错里的禁用词或禁用符号。\n"
        "- 空字段必须根据已有证据补完整，但不能新增事实。\n"
        "- 保持原 JSON 字段和结构不变，只重写不合格表达。"
    )
    return [{**messages[0], "content": messages[0]["content"] + retry_note}, *messages[1:]]


def _should_retry_generation_error(error: Exception) -> bool:
    message = str(error)
    return "contains banned pattern" in message or " is empty" in message


def _quotes_from_card(card: dict[str, Any]) -> list[QuotePreview]:
    return [
        QuotePreview(
            text=str(quote.get("text") or ""),
            community=str(quote.get("community") or ""),
            permalink=str(quote.get("permalink") or ""),
        )
        for quote in card.get("quotes", [])
        if isinstance(quote, dict)
    ]


def _common_draft_payload(card: dict[str, Any]) -> dict[str, Any]:
    quotes = _quotes_from_card(card)
    source_module = card.get("source_module") or {}
    source_communities = [str(item) for item in source_module.get("primary_communities", [])]
    if not source_communities and card.get("top_community"):
        source_communities = [str(card["top_community"])]
    card_id = str(card["card_id"])
    return {
        "draft_id": f"ab-{card_id}",
        "candidate_id": card_id,
        "candidate_ids": [card_id],
        "card_id": f"ab-{card_id}",
        "signal_id": str(card.get("signal_id") or card_id),
        "topic_pack_id": card.get("topic_pack_id"),
        "topic_cluster_id": card.get("topic_cluster_id"),
        "topic_cluster_ids": [str(item) for item in card.get("topic_cluster_ids", [])],
        "named_topic_ids": [str(item) for item in card.get("named_topic_ids", [])],
        "category_id": str(card.get("category_id") or card.get("card_type") or "validate"),
        "title": str(card.get("title") or ""),
        "source_scope_id": str(card.get("source_scope_id") or "ai-automation"),
        "source_scope_name": str(card.get("source_scope_name") or "AI 与自动化"),
        "matched_subreddit": str(card.get("top_community") or "").replace("r/", "", 1),
        "post_id": card_id,
        "source_event_at": None,
        "score": int(card.get("score") or 0),
        "num_comments": int(card.get("num_comments") or 0),
        "time_window": str(card.get("time_window") or "7d"),
        "signal_level": str(card.get("signal_level") or "sustained"),
        "why_now_reason": str(card.get("why_now_reason") or "recurring_7d"),
        "thread_count": int(card.get("thread_count") or 1),
        "community_count": int(card.get("community_count") or 1),
        "quote_count": len(quotes),
        "intent_tags": [str(item) for item in card.get("intent_tags", [])],
        "evidence_quotes": quotes,
        "summary_line": str(card.get("summary_line") or ""),
        "audience": str(card.get("audience") or ""),
        "why_now": str(card.get("why_now") or ""),
        "source_link": str(card.get("source_link") or ""),
        "source_links": [str(card.get("source_link"))] if card.get("source_link") else [],
        "source_communities": source_communities,
        "draft_status": "draft",
        "draft_note": "three tab prompt ab",
    }


def card_to_draft(card: dict[str, Any]) -> ValidationCardDraft | WritingCardDraft:
    lane = str(card.get("lane") or "signal")
    base = _common_draft_payload(card)
    if str(card.get("card_type") or "") == "write":
        detail_payload = card.get("detail") or {}
        return WritingCardDraft(
            **base,
            card_type="write",
            lane="breakdown",
            detail=WritingDetail.model_validate(
                {
                    "thesis": str(detail_payload.get("thesis") or ""),
                    "writing_angle_or_perspective": str(detail_payload.get("writing_angle_or_perspective") or ""),
                    "tension_point_or_why_it_matters": str(detail_payload.get("tension_point_or_why_it_matters") or ""),
                    "title_hooks": [str(item) for item in detail_payload.get("title_hooks", [])],
                    "quote_pack": [str(item) for item in detail_payload.get("quote_pack", [])],
                }
            ),
        )
    return ValidationCardDraft(
        **base,
        card_type="validate",
        lane=lane,
        detail=build_validation_detail(lane, card.get("detail") or {}),
    )


def extract_fields(draft: ValidationCardDraft | WritingCardDraft) -> dict[str, Any]:
    detail = draft.detail.model_dump()
    return {
        "title": draft.title,
        "summary_line": draft.summary_line,
        "audience": draft.audience,
        "why_now": draft.why_now,
        **detail,
    }


def _published_fields(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": str(card.get("title") or ""),
        "summary_line": str(card.get("summary_line") or ""),
        "audience": str(card.get("audience") or ""),
        "why_now": str(card.get("why_now") or ""),
        **(card.get("detail") or {}),
    }


def _messages_for_draft(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    rules: dict[str, Any],
    banned: list[str],
) -> list[dict[str, str]]:
    if isinstance(draft, WritingCardDraft) or draft.lane == "breakdown":
        return build_breakdown_prompt(draft, banned_patterns=banned)
    builder = build_hot_prompt if draft.lane == "hot" else build_signal_prompt
    messages = builder(draft, banned_patterns=banned)
    extra = semantic_prompt_extra(rules=rules, lane=draft.lane, topic_pack_id=draft.topic_pack_id)
    if extra:
        messages[0] = {**messages[0], "content": messages[0]["content"] + extra}
    return messages


def _model_route_for_draft(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    rules: dict[str, Any],
    models: dict[str, Any],
    model_override: str | None,
) -> tuple[str, float, int, dict[str, Any]]:
    if isinstance(draft, WritingCardDraft) or draft.lane == "breakdown":
        timeout = float(rules["timeouts"]["breakdown_seconds"])
        model = model_override or str(models["reasoning_model"])
        return model, timeout, _max_tokens(rules, "breakdown", default=1800), _breakdown_json_schema()
    timeout_default = float(rules["timeouts"]["signal_seconds"])
    model, timeout = resolve_card_content_model_route(
        models=models,
        topic_pack_id=draft.topic_pack_id,
        lane=draft.lane,
        default_timeout=timeout_default,
    )
    if model_override:
        model = model_override
    return model, timeout, _max_tokens(rules, "signal", default=2200), _card_content_json_schema_for_draft(draft)


async def generate_one(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    rules: dict[str, Any],
    models: dict[str, Any],
    banned: list[str],
    variant: bool,
    model_override: str | None,
) -> tuple[dict[str, Any], str]:
    messages = _with_overlay(_messages_for_draft(draft, rules=rules, banned=banned), enabled=variant)
    model, timeout, max_tokens, schema = _model_route_for_draft(
        draft,
        rules=rules,
        models=models,
        model_override=model_override,
    )

    async def _attempt(attempt_messages: list[dict[str, str]]) -> tuple[dict[str, Any], str]:
        payload = await _generate_json(
            model=model,
            timeout=timeout,
            messages=attempt_messages,
            client_factory=lambda selected_model, selected_timeout: build_card_content_client(
                selected_model,
                timeout=selected_timeout,
            ),
            max_tokens=max_tokens,
            response_schema=schema,
        )
        if isinstance(draft, WritingCardDraft) or draft.lane == "breakdown":
            generated = _apply_breakdown_content(draft, payload, rules)
        else:
            generated = _apply_validation_content(draft, payload, rules)
            generated = finalize_validation_readout(generated, source_draft=draft, rules=rules)
        return extract_fields(generated), model

    attempt_messages = messages
    last_error: ValueError | None = None
    for _ in range(3):
        try:
            return await _attempt(attempt_messages)
        except ValueError as exc:
            if not _should_retry_generation_error(exc):
                raise
            last_error = exc
            attempt_messages = _with_retry_instruction(attempt_messages, exc)
    raise last_error or ValueError("generation failed")


def render_markdown_report(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Hotpost 三 Tab Prompt A/B 小样本报告",
        "",
        "这份报告只比较语义表达，不代表候选质量、发布 gate 或小程序 UI 变更。",
        "",
        "## 总览",
        "",
    ]
    for lane in LANE_ORDER:
        lane_rows = [row for row in rows if row["lane"] == lane]
        if not lane_rows:
            continue
        baseline_success = sum(1 for row in lane_rows if not row.get("baseline_error"))
        variant_success = sum(1 for row in lane_rows if not row.get("variant_error"))
        lines.append(
            f"- `{lane}`: baseline {baseline_success}/{len(lane_rows)} 成功，variant {variant_success}/{len(lane_rows)} 成功"
        )
    lines.append("")
    for lane in LANE_ORDER:
        lane_rows = [row for row in rows if row["lane"] == lane]
        if not lane_rows:
            continue
        lines.extend([f"## {lane}", ""])
        for row in lane_rows:
            lines.extend(
                [
                    f"### {row['card_id']}",
                    "",
                    f"- model: `{row.get('model', '')}`",
                    "",
                ]
            )
            if row.get("baseline_error") or row.get("variant_error"):
                lines.extend(
                    [
                        "**generation_error**",
                        "",
                        f"- A baseline: {row.get('baseline_error') or ''}",
                        f"- B variant: {row.get('variant_error') or ''}",
                        "",
                    ]
                )
            field_names = sorted(set(row["baseline"]) | set(row["variant"]))
            for field in field_names:
                baseline = str(row["baseline"].get(field) or "").replace("\n", " ")
                variant = str(row["variant"].get(field) or "").replace("\n", " ")
                if not baseline and not variant:
                    continue
                lines.extend(
                    [
                        f"**{field}**",
                        "",
                        f"- A baseline: {baseline}",
                        f"- B variant: {variant}",
                        "",
                    ]
                )
    return "\n".join(lines).rstrip() + "\n"


async def run_experiment(*, limit_per_lane: int, model_override: str | None) -> list[dict[str, Any]]:
    samples = load_sample_cards(limit_per_lane=limit_per_lane)
    rules = load_card_content_rules()
    models = load_card_content_models()
    banned = _all_banned_patterns(rules)
    rows: list[dict[str, Any]] = []
    for lane in LANE_ORDER:
        for card in samples[lane]:
            draft = card_to_draft(card)
            baseline: dict[str, Any] = {}
            variant: dict[str, Any] = {}
            baseline_error = ""
            variant_error = ""
            model = ""
            variant_model = ""
            try:
                baseline, model = await generate_one(
                    draft,
                    rules=rules,
                    models=models,
                    banned=banned,
                    variant=False,
                    model_override=model_override,
                )
            except Exception as exc:  # noqa: BLE001 - experiment report must keep moving.
                baseline_error = f"{type(exc).__name__}: {exc}"
            try:
                variant, variant_model = await generate_one(
                    draft,
                    rules=rules,
                    models=models,
                    banned=banned,
                    variant=True,
                    model_override=model_override,
                )
            except Exception as exc:  # noqa: BLE001 - experiment report must keep moving.
                variant_error = f"{type(exc).__name__}: {exc}"
            rows.append(
                {
                    "lane": lane,
                    "card_id": card["card_id"],
                    "model": variant_model or model,
                    "published": _published_fields(card),
                    "baseline": baseline,
                    "variant": variant,
                    "baseline_error": baseline_error,
                    "variant_error": variant_error,
                }
            )
            print(
                json.dumps(
                    {
                        "event": "generated",
                        "lane": lane,
                        "card_id": card["card_id"],
                        "model": variant_model or model,
                        "baseline_error": baseline_error,
                        "variant_error": variant_error,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return rows


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v1_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v1_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B")
    parser.add_argument("--limit-per-lane", type=int, default=5)
    parser.add_argument("--model", default="", help="Optional model override for all lanes")
    args = parser.parse_args()

    rows = await run_experiment(
        limit_per_lane=args.limit_per_lane,
        model_override=args.model.strip() or None,
    )
    json_path, md_path = write_outputs(rows)
    print(json.dumps({"event": "done", "json_path": str(json_path), "report_path": str(md_path), "row_count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
