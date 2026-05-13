from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(dotenv_path=ROOT / ".env")

from app.services.hotpost.card_payload_store import load_published_cards, merge_published_cards
from app.services.hotpost.published_card_semantic_refresh import (
    refresh_published_card_semantics,
    select_cards_for_semantic_refresh,
    semantic_change_summary,
)

PLAN_KIND = "published_card_semantic_refresh"
PLAN_VERSION = 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh semantic copy for already published hotpost cards without replacing release state."
    )
    parser.add_argument("--card-id", action="append", default=[], help="Refresh one published card_id. Repeatable.")
    parser.add_argument("--lane", action="append", choices=["signal", "hot", "breakdown"], default=[])
    parser.add_argument("--card-type", action="append", choices=["validate", "write"], default=[])
    parser.add_argument("--limit", type=int, default=None, help="Limit selected cards. Dry-run defaults to 5.")
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Max concurrent refresh workers for dry-run/apply generation. apply-plan ignores this.",
    )
    parser.add_argument("--all", action="store_true", help="Allow selecting all matching published cards.")
    parser.add_argument("--apply", action="store_true", help="Write refreshed cards back via merge_published_cards.")
    parser.add_argument("--output-plan", type=Path, help="Write exact refreshed cards to a reusable plan JSON.")
    parser.add_argument(
        "--apply-plan",
        type=Path,
        help="Apply a previously generated plan JSON without calling refresh generation again.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return parser.parse_args(argv)


async def run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_args(args)
    if args.apply_plan is not None:
        plan = _load_refresh_plan(args.apply_plan)
        refreshed = [entry["refreshed_card"] for entry in plan["cards"]]
        merged = merge_published_cards(refreshed)
        return {
            "mode": "apply_plan",
            "selected": len(refreshed),
            "merged": merged,
            "apply_plan": str(args.apply_plan),
            "cards": [
                {
                    "card_id": entry["card_id"],
                    "lane": entry["lane"],
                    "card_type": entry["card_type"],
                    "changed": entry["changed"],
                }
                for entry in plan["cards"]
            ],
        }

    published = load_published_cards()
    limit = args.limit
    if not args.apply and limit is None:
        limit = 5
    selected = select_cards_for_semantic_refresh(
        published,
        card_ids=set(args.card_id) or None,
        lanes=set(args.lane) or None,
        card_types=set(args.card_type) or None,
        limit=limit,
    )
    refreshed: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    refreshed = await _refresh_cards(selected, workers=args.workers)
    for item, updated in zip(selected, refreshed):
        changes.append(
            {
                "card_id": item.get("card_id"),
                "lane": item.get("lane"),
                "card_type": item.get("card_type"),
                "changed": semantic_change_summary(item, updated),
            }
        )

    plan = _build_refresh_plan(refreshed=refreshed, changes=changes)
    if args.output_plan is not None:
        _write_refresh_plan(args.output_plan, plan)

    merged = merge_published_cards(refreshed) if args.apply else 0
    result = {
        "mode": "apply" if args.apply else "dry_run",
        "selected": len(selected),
        "merged": merged,
        "cards": changes,
    }
    if args.output_plan is not None:
        result["output_plan"] = str(args.output_plan)
    return result


def _validate_args(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be greater than 0")
    if args.workers <= 0:
        raise ValueError("--workers must be greater than 0")
    if args.apply_plan is not None:
        if args.card_id or args.lane or args.card_type or args.all or args.limit is not None or args.output_plan is not None:
            raise ValueError("--apply-plan cannot be combined with selectors, --limit, or --output-plan")
        return
    has_selector = bool(args.card_id or args.lane or args.card_type or args.all)
    if args.apply and not has_selector:
        raise ValueError("--apply requires --card-id, --lane, --card-type, or --all")


def _build_refresh_plan(*, refreshed: list[dict[str, Any]], changes: list[dict[str, Any]]) -> dict[str, Any]:
    change_map = {str(item["card_id"]): item for item in changes}
    return {
        "plan_version": PLAN_VERSION,
        "kind": PLAN_KIND,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "selected": len(refreshed),
        "cards": [
            {
                "card_id": card.get("card_id"),
                "lane": card.get("lane"),
                "card_type": card.get("card_type"),
                "changed": change_map.get(str(card.get("card_id")), {}).get("changed", {}),
                "refreshed_card": card,
            }
            for card in refreshed
        ],
    }


async def _refresh_cards(selected: list[dict[str, Any]], *, workers: int) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(workers)

    async def _runner(item: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await refresh_published_card_semantics(item)

    return list(await asyncio.gather(*(_runner(item) for item in selected)))


def _write_refresh_plan(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_refresh_plan(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"apply plan does not exist: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("apply plan must be a JSON object")
    if raw.get("kind") != PLAN_KIND:
        raise ValueError(f"apply plan kind must be {PLAN_KIND}")
    if raw.get("plan_version") != PLAN_VERSION:
        raise ValueError(f"apply plan version must be {PLAN_VERSION}")
    raw_cards = raw.get("cards")
    if not isinstance(raw_cards, list):
        raise ValueError("apply plan cards must be a list")

    plan_cards: list[dict[str, Any]] = []
    for item in raw_cards:
        if not isinstance(item, dict):
            raise ValueError("apply plan card entries must be JSON objects")
        refreshed_card = item.get("refreshed_card")
        if not isinstance(refreshed_card, dict):
            raise ValueError("apply plan card entry must include refreshed_card")
        plan_cards.append(
            {
                "card_id": item.get("card_id") or refreshed_card.get("card_id"),
                "lane": item.get("lane") or refreshed_card.get("lane"),
                "card_type": item.get("card_type") or refreshed_card.get("card_type"),
                "changed": item.get("changed") if isinstance(item.get("changed"), dict) else {},
                "refreshed_card": refreshed_card,
            }
        )
    return {"cards": plan_cards}


def _print_result(result: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(f"mode={result['mode']} selected={result['selected']} merged={result['merged']}")
    if result.get("output_plan"):
        print(f"output_plan={result['output_plan']}")
    if result.get("apply_plan"):
        print(f"apply_plan={result['apply_plan']}")
    for card in result["cards"]:
        print(f"\n[{card['card_id']}] {card['lane']} / {card['card_type']}")
        changed = card["changed"]
        if not changed:
            print("  no semantic changes")
            continue
        print(json.dumps(changed, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        result = asyncio.run(run(args))
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    _print_result(result, as_json=args.json)


if __name__ == "__main__":
    main()
