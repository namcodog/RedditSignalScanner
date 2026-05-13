from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.hot_lane_eval_set_builder import build_hot_lane_eval_artifacts


OUT_DIR = ROOT / "reports" / "evals"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main() -> None:
    load_backend_env()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = build_hot_lane_eval_artifacts()
    _write_jsonl(OUT_DIR / "hot_lane_eval_set_v1.jsonl", artifacts["real_cases"])
    _write_jsonl(OUT_DIR / "hot_lane_eval_labels_v1.jsonl", artifacts["labels"])
    (OUT_DIR / "hot_lane_eval_manifest_v1.json").write_text(
        json.dumps(artifacts["manifest"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifacts["manifest"], ensure_ascii=False))


if __name__ == "__main__":
    main()
