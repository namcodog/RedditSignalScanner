from __future__ import annotations

import json
from pathlib import Path
from collections import Counter
from typing import Optional, Any, Awaitable, Callable, Protocol

from app.services.hotpost.card_content_generator import load_card_content_models
from app.services.llm.clients.openai_client import OpenAIChatClient


class JudgeClient(Protocol):
    async def generate(
        self,
        prompt: str | list[dict[str, str]],
        *,
        response_format:Optional[ dict[str, str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str: ...


JudgeClientFactory = Callable[[str, float], JudgeClient]


def _default_client_factory(model: str, timeout: float) -> JudgeClient:
    return OpenAIChatClient(model=model, timeout=timeout)


async def run_signal_judge(
    case: dict[str, Any],
    *,
    prompt_path: Path,
    client_factory: JudgeClientFactory = _default_client_factory,
) -> dict[str, Any]:
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    model = load_card_content_models()["reasoning_model"]
    client = client_factory(model, 30.0)
    raw = await client.generate(
        _build_messages(prompt, case),
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=900,
    )
    payload = _parse_json_object(raw)
    if not isinstance(payload, dict):
        raise ValueError("judge payload must be object")
    return {
        "eval_case_id": case["eval_case_id"],
        "overall_pass": bool(payload.get("overall_pass")),
        "field_passes": payload.get("field_passes") or {},
        "failure_tags": [str(tag) for tag in (payload.get("failure_tags") or [])][:3],
        "review_notes": str(payload.get("review_notes") or "").strip(),
    }


def _parse_json_object(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(raw[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("judge payload must be object")
    return payload


def compare_judgments(
    *,
    predictions: list[dict[str, Any]],
    labels: list[dict[str, Any]],
) -> dict[str, Any]:
    label_map = {item["eval_case_id"]: item for item in labels}
    total = len(predictions)
    overall_match = 0
    exact_tag_match = 0
    mismatches: list[dict[str, Any]] = []
    for prediction in predictions:
        label = label_map[prediction["eval_case_id"]]
        overall_same = prediction["overall_pass"] == label["overall_pass"]
        tags_same = set(prediction["failure_tags"]) == set(label["failure_tags"])
        if overall_same:
            overall_match += 1
        if tags_same:
            exact_tag_match += 1
        if not overall_same or not tags_same:
            mismatches.append(
                {
                    "eval_case_id": prediction["eval_case_id"],
                    "predicted_overall_pass": prediction["overall_pass"],
                    "human_overall_pass": label["overall_pass"],
                    "predicted_failure_tags": prediction["failure_tags"],
                    "human_failure_tags": label["failure_tags"],
                }
            )
    return {
        "sample_count": total,
        "overall_match_count": overall_match,
        "overall_match_rate": round(overall_match / total, 4) if total else 0.0,
        "exact_tag_match_count": exact_tag_match,
        "exact_tag_match_rate": round(exact_tag_match / total, 4) if total else 0.0,
        "mismatches": mismatches,
    }


def summarize_predictions(predictions: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_map = {case["eval_case_id"]: case for case in cases}
    pass_count = sum(1 for item in predictions if item["overall_pass"])
    fail_count = len(predictions) - pass_count
    fail_tags = Counter(tag for item in predictions if not item["overall_pass"] for tag in item["failure_tags"])
    scope_pass = Counter()
    scope_fail = Counter()
    for item in predictions:
        scope_id = case_map[item["eval_case_id"]]["input_bundle"]["source_scope_id"]
        if item["overall_pass"]:
            scope_pass[scope_id] += 1
        else:
            scope_fail[scope_id] += 1
    return {
        "sample_count": len(predictions),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": round(pass_count / len(predictions), 4) if predictions else 0.0,
        "fail_rate": round(fail_count / len(predictions), 4) if predictions else 0.0,
        "top_failure_tags": fail_tags.most_common(8),
        "scope_pass_counts": dict(scope_pass),
        "scope_fail_counts": dict(scope_fail),
    }


def _build_messages(prompt: str, case: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": json.dumps(
                {"input_bundle": case["input_bundle"], "baseline_output": case["baseline_output"]},
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]


__all__ = ["compare_judgments", "run_signal_judge", "summarize_predictions"]
