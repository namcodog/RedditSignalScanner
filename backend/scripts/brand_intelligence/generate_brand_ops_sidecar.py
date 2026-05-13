from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.scripts_support.env_loader import load_backend_env

load_backend_env()

from app.db.session import SessionFactory
from app.models.brand_registry import BrandRegistry
from app.services.brand_intelligence.brand_ops_sidecar import (
    build_brand_ops_sidecar,
    render_brand_ops_sidecar_markdown,
)
from scripts.import_safety import ensure_dev_or_test_database

TODAY = date.today().isoformat()
REPORT_DIR = PROJECT_ROOT / "reports" / "brand-intelligence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate daily Brand Intelligence sidecar."
    )
    parser.add_argument("--date", default=TODAY)
    parser.add_argument(
        "--digest-input", type=Path, default=REPORT_DIR / f"brand-digest-{TODAY}.json"
    )
    parser.add_argument(
        "--quality-input",
        type=Path,
        default=REPORT_DIR / f"brand-quality-review-{TODAY}.json",
    )
    parser.add_argument("--registry-write-input", type=Path)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=REPORT_DIR / f"brand-ops-sidecar-{TODAY}.json",
    )
    parser.add_argument(
        "--md-output", type=Path, default=REPORT_DIR / f"brand-ops-sidecar-{TODAY}.md"
    )
    parser.add_argument(
        "--semantic-queue-output",
        type=Path,
        default=REPORT_DIR / f"brand-semantic-review-queue-{TODAY}.json",
    )
    parser.add_argument("--skip-db", action="store_true")
    return parser.parse_args()


async def load_known_brand_keys(*, skip_db: bool) -> frozenset[str]:
    if skip_db:
        return frozenset()
    ensure_dev_or_test_database()
    async with SessionFactory() as session:
        result = await session.execute(select(BrandRegistry.brand_key))
    return frozenset(str(value) for value in result.scalars().all())


def main() -> None:
    args = parse_args()
    known_brand_keys = asyncio.run(load_known_brand_keys(skip_db=bool(args.skip_db)))
    payload = build_brand_ops_sidecar(
        report_date=str(args.date),
        digest_payload=_load_json(args.digest_input),
        quality_payload=_load_json(args.quality_input),
        registry_write_payload=_optional_json(args.registry_write_input),
        known_brand_keys=known_brand_keys,
    )
    _write_outputs(
        payload,
        json_path=args.json_output,
        md_path=args.md_output,
        queue_path=args.semantic_queue_output,
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))


def _write_outputs(
    payload: dict[str, object], *, json_path: Path, md_path: Path, queue_path: Path
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_brand_ops_sidecar_markdown(payload), encoding="utf-8")
    queue_path.write_text(
        json.dumps(
            {
                "report_date": payload["report_date"],
                "auto_write_semantic_lexicon": False,
                "items": payload["semantic_review_queue"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _optional_json(path: Path | None) -> dict[str, object] | None:
    return _load_json(path) if path and path.exists() else None


def _load_json(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    main()
