"""Three-tab Hotpost prompt A/B v5 two-stage comparison.

Gemini Flash produces the English semantic brief. DeepSeek V4 Pro writes the
final Chinese card fields through OpenRouter. This read-only runner keeps v4
artifacts intact by writing distinct v5 outputs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request

from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v1 as v1
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v3 as v3
from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v4 as v4

from app.services.hotpost.card_content_generator import (
    _coerce_llm_json_payload,
    _invalid_json_retry_messages,
)
from app.services.llm.clients.openai_client import resolve_llm_api_key
from app.services.llm.interfaces import LLMClientError


REPORTS_EVALS_DIR = v4.REPORTS_EVALS_DIR
SEMANTIC_MODEL = "google/gemini-3-flash-preview"
WRITER_MODEL = "deepseek/deepseek-v4-pro"
BASELINE_MODEL = v4.BASELINE_MODEL


def render_v5_markdown_report(rows: list[dict[str, Any]]) -> str:
    report = v4.render_v4_markdown_report(rows)
    return report.replace(
        "# Hotpost 三 Tab Prompt A/B v4 two-stage 小样本报告",
        "# Hotpost 三 Tab Prompt A/B v5 flash-deepseek 小样本报告",
        1,
    )


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    REPORTS_EVALS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v5_flash_deepseek_results.json"
    md_path = REPORTS_EVALS_DIR / "hotpost_three_tab_prompt_ab_v5_flash_deepseek_report.md"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_v5_markdown_report(rows), encoding="utf-8")
    return json_path, md_path


async def _generate_json_without_response_format(
    *,
    model: str,
    timeout: float,
    messages: list[dict[str, str]],
    client_factory=None,
    max_tokens: int,
) -> dict[str, Any]:
    raw = await _generate_text_without_response_format(
        model=model,
        timeout=timeout,
        messages=messages,
        client_factory=client_factory,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    try:
        return _coerce_llm_json_payload(raw)
    except ValueError:
        retry_messages = _invalid_json_retry_messages(messages, model=model, attempt=1)
        raw = await _generate_text_without_response_format(
            model=model,
            timeout=timeout,
            messages=retry_messages,
            client_factory=client_factory,
            temperature=0.0,
            max_tokens=max_tokens,
        )
        return _coerce_llm_json_payload(raw)


async def _generate_text_without_response_format(
    *,
    model: str,
    timeout: float,
    messages: list[dict[str, str]],
    client_factory,
    temperature: float,
    max_tokens: int,
) -> str:
    if client_factory is not None:
        client = client_factory(model, timeout)
        return await client.generate(
            messages,
            response_format=None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    return await asyncio.to_thread(
        _raw_openrouter_chat_completion,
        model=model,
        timeout=timeout,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _raw_openrouter_chat_completion(
    *,
    model: str,
    timeout: float,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    base = os.getenv("OPENAI_BASE", "https://openrouter.ai/api/v1").rstrip("/")
    api_key = resolve_llm_api_key(base_url=base)
    if not api_key:
        raise LLMClientError("openrouter", "missing API key")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=max(2.0, float(timeout))) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LLMClientError("openrouter", body or "HTTP request failed", status_code=exc.code) from exc
    except Exception as exc:
        raise LLMClientError("openrouter", str(exc) or "connection failed") from exc
    choices = data.get("choices") or []
    if not choices:
        raise LLMClientError("openrouter", "empty choices")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMClientError("openrouter", "empty content")
    return content


async def _generate_deepseek_fields_from_messages(
    draft: v1.ValidationCardDraft | v1.WritingCardDraft,
    *,
    rules: dict[str, Any],
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    async def _attempt(attempt_messages: list[dict[str, str]]) -> dict[str, Any]:
        payload = await _generate_json_without_response_format(
            model=model,
            timeout=timeout,
            messages=attempt_messages,
            max_tokens=max_tokens,
        )
        if isinstance(draft, v1.WritingCardDraft) or draft.lane == "breakdown":
            generated = v1._apply_breakdown_content(draft, payload, rules)
        else:
            generated = v1._apply_validation_content(draft, payload, rules)
            generated = v1.finalize_validation_readout(generated, source_draft=draft, rules=rules)
        return v1.extract_fields(generated)

    attempt_messages = messages
    last_error: ValueError | None = None
    for _ in range(3):
        try:
            return await _attempt(attempt_messages)
        except ValueError as exc:
            if not v1._should_retry_generation_error(exc):
                raise
            last_error = exc
            attempt_messages = v1._with_retry_instruction(attempt_messages, exc)
    raise last_error or ValueError("generation failed")


async def _generate_one_two_stage(
    draft: v1.ValidationCardDraft | v1.WritingCardDraft,
    *,
    card: dict[str, Any],
    rules: dict[str, Any],
    models: dict[str, Any],
    banned: list[str],
    baseline_model: str,
    semantic_model: str,
    writer_model: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    baseline, _ = await v1.generate_one(
        draft,
        rules=rules,
        models=models,
        banned=banned,
        variant=True,
        model_override=baseline_model,
    )
    published = v1._published_fields(card)
    semantic_brief = await v4.generate_semantic_brief(
        lane=str(card.get("lane") or ""),
        card_id=str(card.get("card_id") or ""),
        published=published,
        baseline=baseline,
        variant_v3=baseline,
        model=semantic_model,
    )
    writer_base_messages = v1._with_overlay(
        v1._messages_for_draft(draft, rules=rules, banned=banned),
        enabled=True,
    )
    model, timeout, max_tokens, _schema = v1._model_route_for_draft(
        draft,
        rules=rules,
        models=models,
        model_override=writer_model,
    )
    writer_messages = v4.build_writer_messages(writer_base_messages, semantic_brief=semantic_brief)
    variant = await _generate_deepseek_fields_from_messages(
        draft,
        rules=rules,
        messages=writer_messages,
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return baseline, variant, semantic_brief


async def run_experiment(
    *,
    limit_per_lane: int,
    baseline_model: str,
    semantic_model: str,
    writer_model: str,
) -> list[dict[str, Any]]:
    original_overlay = v1.build_plain_language_overlay
    v1.build_plain_language_overlay = v3.build_v3_semantic_overlay
    try:
        samples = v1.load_sample_cards(limit_per_lane=limit_per_lane)
        rules = v4.with_v4_banned_patterns(v1.load_card_content_rules())
        models = v1.load_card_content_models()
        banned = v1._all_banned_patterns(rules)
        rows: list[dict[str, Any]] = []
        model_label = f"{semantic_model} -> {writer_model}"
        for lane in v1.LANE_ORDER:
            for card in samples[lane]:
                draft = v1.card_to_draft(card)
                baseline: dict[str, Any] = {}
                variant: dict[str, Any] = {}
                semantic_brief: dict[str, Any] = {}
                baseline_error = ""
                variant_error = ""
                try:
                    baseline, variant, semantic_brief = await _generate_one_two_stage(
                        draft,
                        card=card,
                        rules=rules,
                        models=models,
                        banned=banned,
                        baseline_model=baseline_model,
                        semantic_model=semantic_model,
                        writer_model=writer_model,
                    )
                except Exception as exc:  # noqa: BLE001 - experiment report must keep moving.
                    variant_error = f"{type(exc).__name__}: {exc}"
                rows.append(
                    {
                        "lane": lane,
                        "card_id": card["card_id"],
                        "model": model_label,
                        "published": v1._published_fields(card),
                        "semantic_brief": semantic_brief,
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
                            "model": model_label,
                            "variant_error": variant_error,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
        return rows
    finally:
        v1.build_plain_language_overlay = original_overlay



async def main() -> None:
    parser = argparse.ArgumentParser(description="Run three-tab Hotpost prompt A/B v5 flash-deepseek")
    parser.add_argument("--limit-per-lane", type=int, default=2)
    parser.add_argument("--baseline-model", default=BASELINE_MODEL)
    parser.add_argument("--semantic-model", default=SEMANTIC_MODEL)
    parser.add_argument("--writer-model", default=WRITER_MODEL)
    args = parser.parse_args()

    rows = await run_experiment(
        limit_per_lane=args.limit_per_lane,
        baseline_model=args.baseline_model.strip() or BASELINE_MODEL,
        semantic_model=args.semantic_model.strip() or SEMANTIC_MODEL,
        writer_model=args.writer_model.strip() or WRITER_MODEL,
    )
    json_path, md_path = write_outputs(rows)
    print(
        json.dumps(
            {"event": "done", "json_path": str(json_path), "report_path": str(md_path), "row_count": len(rows)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
