from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _is_placeholder(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return not normalized or normalized.startswith("your_") or "example" in normalized or normalized == "replace_me"


for key, value in dotenv_values(BACKEND_ROOT / ".env").items():
    if value is not None and _is_placeholder(os.getenv(key)):
        os.environ[key] = str(value)

from app.core.config import settings
from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.reddit_candidate_mapper import build_candidate_pack
from app.services.hotpost.reddit_search_spec_builder import build_reddit_search_specs
from app.services.hotpost.signal_judge_runner import run_signal_judge, summarize_predictions
from app.services.hotpost.source_scope_candidate_collector import _fetch_posts, _is_noise_post, _pack_candidate_cap
from app.services.infrastructure.reddit_client import RedditAPIClient

from app.services.hotpost import card_content_generator as generator_module


EVALS_DIR = ROOT / "reports" / "evals"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


async def _build_live_candidates() -> list[CandidatePack]:
    specs = [spec for spec in build_reddit_search_specs("ecommerce-sellers") if spec.topic_pack_id == "category-winds"]
    collected_at = datetime.now(timezone.utc)
    found: list[CandidatePack] = []
    async with RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        request_timeout=20.0,
        search_timeout=12.0,
        max_concurrency=2,
    ) as reddit:
        for spec in specs[:12]:
            posts = await _fetch_posts(reddit, spec)
            filtered_posts = [post for post in posts if not _is_noise_post(post, spec.topic_pack_id)]
            for post in filtered_posts[: _pack_candidate_cap(spec.topic_pack_id)]:
                comments = await reddit.fetch_post_comments(post.id, sort="top", depth=1, limit=5, mode="topn")
                candidate = build_candidate_pack(spec, post, comments, collect_batch_id="category-winds-canary", collected_at=collected_at)
                if candidate:
                    found.append(candidate)
            if len(found) >= 2:
                break
    return found


async def _judge_rows(rows: list[dict]) -> dict:
    predictions = await asyncio.gather(*(run_signal_judge(row, prompt_path=EVALS_DIR / "signal_judge_prompt_v1.md") for row in rows))
    return {"predictions": predictions, "summary": summarize_predictions(predictions, rows)}


async def main() -> None:
    candidates = await _build_live_candidates()
    cohort = {"case_count": len(candidates), "candidates": [item.model_dump(mode="json") for item in candidates]}
    (EVALS_DIR / "category_winds_canary_cohort_v1.json").write_text(json.dumps(cohort, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    semantic_rows: list[dict] = []
    for candidate in candidates:
        draft = seed_validation_draft(candidate)
        generated_draft = await generator_module.generate_card_content(draft)
        case_id = f"category-winds-{candidate.candidate_id}"
        semantic_rows.append(
            {
                "eval_case_id": case_id,
                "variant_id": "category_winds_semantic_readout_v1",
                "input_bundle": {
                    "source_scope_id": candidate.source_scope_id,
                    "source_scope_name": candidate.source_scope_name,
                    "topic_pack_id": candidate.topic_pack_id,
                    "signal_level": candidate.signal_level,
                    "why_now_reason": candidate.why_now_reason,
                    "intent_tags": candidate.intent_tags,
                    "thread_count": candidate.thread_count,
                    "community_count": candidate.community_count,
                    "quote_count": candidate.quote_count,
                    "source_communities": candidate.top_communities,
                    "evidence_quotes": [quote.model_dump(mode="json") for quote in candidate.evidence_quotes],
                },
                "baseline_output": {
                    "title": generated_draft.title,
                    "summary_line": generated_draft.summary_line,
                    "audience": generated_draft.audience,
                    "why_now": generated_draft.why_now,
                    "detail": generated_draft.detail.model_dump(mode="json"),
                },
            }
        )

    semantic = await _judge_rows(semantic_rows)
    _write_jsonl(EVALS_DIR / "category_winds_canary_semantic_readout_v1_outputs_v1.jsonl", semantic_rows)
    _write_jsonl(EVALS_DIR / "category_winds_canary_semantic_readout_v1_judge_v1.jsonl", semantic["predictions"])
    (EVALS_DIR / "category_winds_canary_semantic_readout_v1_summary_v1.json").write_text(
        json.dumps(semantic["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    keep_discard = [
        {
            "variant_id": "category_winds_semantic_readout_v1",
            "pass_rate": float(semantic["summary"]["pass_rate"]),
            "pass_count": semantic["summary"]["pass_count"],
            "fail_count": semantic["summary"]["fail_count"],
            "decision": "production",
        },
    ]
    (EVALS_DIR / "category_winds_canary_keep_discard_v1.json").write_text(json.dumps(keep_discard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(keep_discard, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
