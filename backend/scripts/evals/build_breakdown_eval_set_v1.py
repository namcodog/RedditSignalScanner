from __future__ import annotations

import asyncio
import json
import os
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


def _load_backend_env() -> None:
    for key, value in dotenv_values(BACKEND_ROOT / ".env").items():
        if value is None:
            continue
        if _is_placeholder(os.getenv(key)):
            os.environ[key] = str(value)


_load_backend_env()

from app.services.hotpost.breakdown_eval_set_builder import build_breakdown_eval_artifacts

OUT_DIR = ROOT / "reports" / "evals"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = await build_breakdown_eval_artifacts(report_progress=lambda message: print(f"[breakdown-eval] {message}", flush=True))
    _write_jsonl(OUT_DIR / "breakdown_eval_set_v1.jsonl", artifacts["real_cases"])
    _write_jsonl(OUT_DIR / "breakdown_eval_labels_v1.jsonl", artifacts["labels"])
    _write_jsonl(OUT_DIR / "breakdown_eval_synthetic_plan_v1.jsonl", artifacts["synthetic_plan"])
    _write_jsonl(OUT_DIR / "breakdown_eval_generation_failures_v1.jsonl", artifacts["generation_failures"])
    (OUT_DIR / "breakdown_eval_manifest_v1.json").write_text(
        json.dumps(artifacts["manifest"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifacts["manifest"], ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
