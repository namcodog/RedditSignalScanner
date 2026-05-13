#!/usr/bin/env python3
"""Codex OAuth Batch Comment Labeler (v3 — direct httpx + SSE)

Uses ~/.codex/auth.json access_token to call gpt-5.3-codex via
ChatGPT Backend API (chatgpt.com/backend-api/codex/responses).
Zero API cost — uses ChatGPT subscription quota.

Flow:
  1. export_llm_label_candidates.py → candidates.jsonl
  2. THIS SCRIPT reads candidates.jsonl → calls API → writes results.jsonl
  3. import_client_llm_labels.py --comments results.jsonl → DB

Prerequisites:
  pip install httpx
  codex login  # authenticate first (creates ~/.codex/auth.json)

Usage:
  # Step 1: Export candidates
  cd backend && PYTHONPATH=. python scripts/report/export_llm_label_candidates.py \\
    --comments-limit 10000 --lookback-days 365 --out /tmp/candidates.jsonl

  # Step 2: Run this labeler
  PYTHONPATH=. python scripts/import/codex_batch_labeler.py \\
    --input /tmp/candidates.jsonl \\
    --output /tmp/results.jsonl \\
    --batch-size 10

  # Step 3: Import results
  PYTHONPATH=. python scripts/import/import_client_llm_labels.py \\
    --comments /tmp/results.jsonl \\
    --model-name gpt-5.3-codex \\
    --prompt-version codex-oauth-v1

【离线合同 — Phase A】
  - 此脚本为离线低成本批量打标通道，仅作为人工离线工具使用
  - 禁止把此脚本改成 Celery worker 依赖，禁止在 Celery 任务中直接 import 本模块
  - 禁止把 ~/.codex/auth.json 当作服务端运行时凭据（token 会过期且不受 secrets 管理）
  - 此脚本的典型场景：历史评论 backlog 补标、训练集建设、高价值评论离线精标
  - 输出结果必须保留 model_name / prompt_version / 离线来源标记（codex_oauth_offline）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# ─── Constants ───────────────────────────────────────────────────────
CODEX_AUTH_PATH = Path.home() / ".codex" / "auth.json"
CODEX_API_URL = "https://chatgpt.com/backend-api/codex/responses"

DEFAULT_MODEL = "gpt-5.3-codex"
DEFAULT_BATCH_SIZE = 10
DEFAULT_RPM = 20  # requests per minute (conservative for subscription)
DEFAULT_REASONING = "low"  # low | medium | high

# Available models (ChatGPT subscription):
#   gpt-5.3-codex       — default, strong coding/reasoning
#   gpt-5.3-codex-spark — ultra-fast (Cerebras), Pro only
#   gpt-5.4             — latest flagship
#   gpt-5.2-codex       — older, still available

# Compact schema — minimal tokens
# Full field names in output, but prompt uses terse description
SCHEMA_STR = (
    '{id:int,actor_type:"buyer_ask|buyer_review|seller_operator|expert_sharing|other",'
    'main_intent:"complain|ask_help|share_solution|recommend_product|offtopic",'
    'sentiment:float(-1~1),pain_tags:[str],aspect_tags:[str],'
    'purchase_intent_score:float(0~1)}'
)

SYSTEM_INSTRUCTIONS = "Classifier. Return JSON array only. No markdown."

PROGRESS_SUFFIX = ".progress"


# ─── Auth ────────────────────────────────────────────────────────────
def load_access_token() -> str:
    """Read access_token from ~/.codex/auth.json"""
    if not CODEX_AUTH_PATH.exists():
        print(
            "❌ ~/.codex/auth.json not found.\n"
            "   Run: codex login",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(CODEX_AUTH_PATH, "r") as f:
        data = json.load(f)

    tokens = data.get("tokens") or {}
    token = tokens.get("access_token")
    if not token:
        print("❌ No access_token in auth.json. Run: codex login", file=sys.stderr)
        sys.exit(1)

    last_refresh = data.get("last_refresh", "unknown")
    print(f"🔑 Token loaded (last refresh: {last_refresh})")
    return token


# ─── API Call (SSE streaming) ────────────────────────────────────────
def build_label_prompt(items: list[dict[str, Any]]) -> str:
    """Build compact labeling prompt — optimized for minimal tokens."""
    # Only send id + truncated comment text (no subreddit, no post_title)
    rows = []
    for item in items:
        cid = item.get("id")
        body = (item.get("comment_body") or item.get("body") or "")[:250]
        rows.append(f"{cid}|{body}")

    return (
        f"Label each. Schema:{SCHEMA_STR}\n"
        f"id|text:\n" + "\n".join(rows)
    )


def call_codex_stream(
    token: str,
    model: str,
    items: list[dict[str, Any]],
    timeout: float = 120.0,
    reasoning: str = DEFAULT_REASONING,
) -> list[dict[str, Any]]:
    """Call Codex Responses API via SSE streaming."""
    prompt = build_label_prompt(items)

    try:
        payload: dict[str, Any] = {
            "model": model,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": [{"role": "user", "content": prompt}],
            "store": False,
            "stream": True,
        }
        if reasoning:
            payload["reasoning"] = {"effort": reasoning}

        with httpx.stream(
            "POST",
            CODEX_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        ) as resp:
            if resp.status_code == 401:
                print("❌ Token expired. Run: codex login", file=sys.stderr)
                sys.exit(1)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", "60"))
                print(f"⏳ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                return call_codex_stream(token, model, items, timeout)
            if resp.status_code != 200:
                error_body = resp.read().decode()
                print(f"⚠️ API error {resp.status_code}: {error_body[:200]}", file=sys.stderr)
                return []

            # Collect SSE delta events
            full_text = ""
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    break
                try:
                    evt = json.loads(payload)
                    etype = evt.get("type", "")
                    if etype == "response.output_text.delta":
                        full_text += evt.get("delta", "")
                except json.JSONDecodeError:
                    pass

    except httpx.TimeoutException:
        print("⚠️ Request timeout", file=sys.stderr)
        return []
    except Exception as e:
        err = str(e)
        if "429" in err or "rate" in err.lower():
            print("⏳ Rate limited. Waiting 60s...")
            time.sleep(60)
            return call_codex_stream(token, model, items, timeout)
        print(f"⚠️ Request error: {e}", file=sys.stderr)
        return []

    # Parse JSON from collected text
    return _parse_json_output(full_text)


def _parse_json_output(text: str) -> list[dict[str, Any]]:
    """Parse JSON array from LLM output, handling code fences."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("results", "comments", "items", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            if "id" in parsed:
                return [parsed]
        return []
    except json.JSONDecodeError:
        print(f"⚠️ JSON parse error: {text[:200]}", file=sys.stderr)
        return []


# ─── I/O ─────────────────────────────────────────────────────────────
def read_jsonl(path: Path) -> list[dict[str, Any]]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def load_progress(output_path: Path) -> set[int]:
    progress_path = Path(str(output_path) + PROGRESS_SUFFIX)
    if not progress_path.exists():
        return set()
    done_ids: set[int] = set()
    with open(progress_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    done_ids.add(int(line))
                except ValueError:
                    pass
    return done_ids


def save_progress(output_path: Path, ids: list[int]) -> None:
    progress_path = Path(str(output_path) + PROGRESS_SUFFIX)
    with open(progress_path, "a") as f:
        for id_ in ids:
            f.write(f"{id_}\n")


def append_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ─── Main ────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Codex OAuth Batch Comment Labeler (zero-cost via ChatGPT subscription)"
    )
    parser.add_argument("--input", required=True, help="Input JSONL (from export)")
    parser.add_argument("--output", required=True, help="Output JSONL (for import)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help="Model: gpt-5.3-codex | gpt-5.3-codex-spark | gpt-5.4")
    parser.add_argument("--reasoning", default=DEFAULT_REASONING,
                        choices=["low", "medium", "high"],
                        help="Reasoning effort (default: low)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--rpm", type=int, default=DEFAULT_RPM)
    parser.add_argument("--max-items", type=int, default=0, help="0=all")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Load token
    token = load_access_token()

    # Load input
    all_items = read_jsonl(input_path)
    all_items = [i for i in all_items if i.get("task_type") == "comment_label"]
    print(f"📄 Loaded {len(all_items)} comment candidates")

    # Resume support
    if args.resume:
        done_ids = load_progress(output_path)
        print(f"♻️ Resuming: {len(done_ids)} already processed")
        all_items = [i for i in all_items if i.get("id") not in done_ids]

    if args.max_items > 0:
        all_items = all_items[: args.max_items]

    if not all_items:
        print("✅ Nothing to process")
        return

    print(
        f"🚀 Processing {len(all_items)} items "
        f"({args.batch_size}/batch, ~{args.rpm} RPM, "
        f"model={args.model}, reasoning={args.reasoning})"
    )

    delay = 60.0 / args.rpm
    processed = 0
    errors = 0
    start_time = time.time()

    for i in range(0, len(all_items), args.batch_size):
        batch = all_items[i: i + args.batch_size]
        batch_ids = [item.get("id") for item in batch]

        try:
            results = call_codex_stream(token, args.model, batch, reasoning=args.reasoning)
            if results:
                append_jsonl(output_path, results)
                save_progress(output_path, batch_ids)
                processed += len(results)
            else:
                errors += len(batch)
        except Exception as e:
            print(f"⚠️ Batch error: {e}", file=sys.stderr)
            errors += len(batch)

        # Progress
        elapsed = time.time() - start_time
        total = len(all_items)
        done_count = i + len(batch)
        rate = done_count / elapsed if elapsed > 0 else 0
        eta = (total - done_count) / rate if rate > 0 else 0
        print(
            f"  [{done_count}/{total}] "
            f"✅ {processed} labeled, ❌ {errors} errors, "
            f"⏱️ {elapsed:.0f}s, ETA {eta:.0f}s"
        )

        if i + args.batch_size < len(all_items):
            time.sleep(delay)

    elapsed = time.time() - start_time
    print(
        f"\n{'='*50}\n"
        f"🏁 Done! {processed} labeled, {errors} errors in {elapsed:.0f}s\n"
        f"📄 Results: {output_path}\n"
        f"\n📥 Import command:\n"
        f"  cd backend && PYTHONPATH=. python scripts/import/import_client_llm_labels.py \\\n"
        f"    --comments {output_path} \\\n"
        f"    --model-name {args.model} \\\n"
        f"    --prompt-version codex-oauth-v1"
    )


if __name__ == "__main__":
    main()
