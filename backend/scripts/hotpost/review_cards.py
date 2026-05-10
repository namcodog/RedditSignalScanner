from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.services.hotpost.card_candidate_store import list_candidates
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.card_selection_policy import (
    build_lane_mix_snapshot,
    build_scope_mix_snapshot,
    prioritize_validate_candidates,
    score_validate_candidate,
)
from app.services.hotpost.card_draft_store import delete_draft, list_drafts, publish_draft, update_draft
from app.services.hotpost.card_payload_store import load_published_cards
from app.services.hotpost.card_review_rejection_store import save_review_rejection
from app.services.hotpost.review_queue_policy import filter_actionable_candidates
from app.services.hotpost.review_card_ops import seed_review_draft, seed_review_draft_from_candidate, seed_review_group_draft
from app.services.hotpost.review_queue_snapshot_store import get_snapshot_candidate, write_review_queue_snapshot


def main() -> None:
    load_backend_env()
    parser = argparse.ArgumentParser(description="Hotpost 审核入口")
    sub = parser.add_subparsers(dest="cmd", required=True)
    queue = sub.add_parser("queue")
    queue.add_argument("--scope")
    queue.add_argument("--level")
    queue.add_argument("--type")
    queue.add_argument("--limit", type=int, default=10)
    seed = sub.add_parser("seed")
    seed.add_argument("candidate_id")
    seed.add_argument("card_type", choices=["validate", "write"])
    seed.add_argument("--snapshot-id")
    seed.add_argument("--live", action="store_true")
    seed_group = sub.add_parser("seed-group")
    seed_group.add_argument("card_type", choices=["validate", "write"])
    seed_group.add_argument("candidate_ids", nargs="+")
    show = sub.add_parser("show-draft")
    show.add_argument("draft_id")
    update = sub.add_parser("update-draft")
    update.add_argument("json_path")
    reject = sub.add_parser("reject")
    reject.add_argument("candidate_id")
    reject.add_argument("--reason", required=True)
    reject.add_argument("--note", default="")
    publish = sub.add_parser("publish")
    publish.add_argument("draft_id")
    args = parser.parse_args()
    {
        "queue": queue_cmd,
        "seed": seed_cmd,
        "seed-group": seed_group_cmd,
        "show-draft": show_cmd,
        "update-draft": update_cmd,
        "reject": reject_cmd,
        "publish": publish_cmd,
    }[args.cmd](args)


def queue_cmd(args: argparse.Namespace) -> None:
    published_items = load_published_cards()
    draft_items = [item.model_dump(mode="json") for item in list_drafts()]
    candidates = filter_actionable_candidates(
        list_candidates(args.scope, args.level),
        card_type=args.type,
        published_items=published_items,
        draft_items=draft_items,
    )
    if args.type != "write":
        candidates = prioritize_validate_candidates(candidates, published_items=published_items)
    candidates = candidates[: args.limit]
    drafts = list_drafts(args.scope, args.type)[: args.limit]
    snapshot_id = write_review_queue_snapshot(
        card_type=args.type,
        scope=args.scope,
        level=args.level,
        limit=args.limit,
        candidates=candidates,
    )
    print(f"snapshot_id={snapshot_id} | candidates={len(candidates)}")
    print("== candidates ==")
    for item in candidates:
        print(f"{item.candidate_id} | {item.source_scope_name} | {item.signal_level} | {item.score}/{item.num_comments} | {item.title}")
        if args.type != "write":
            _, reasons = score_validate_candidate(
                item,
                recent_scope_mix=build_scope_mix_snapshot(published_items),
                recent_lane_mix=build_lane_mix_snapshot(published_items),
            )
            print(f"  lane={seed_validation_draft(item).lane} | priority={', '.join(reasons) or '-'}")
        print(
            f"  reason={item.primary_reason} | source={item.listing_source} | keywords={', '.join(item.matched_keywords) or '-'} | communities={', '.join(item.top_communities)}"
        )
    print("\n== drafts ==")
    for item in drafts:
        print(f"{item.draft_id} | {item.card_type} | {item.source_scope_name} | {item.title}")


def seed_cmd(args: argparse.Namespace) -> None:
    if args.live:
        draft = __import__("asyncio").run(seed_review_draft(args.candidate_id, args.card_type))
    else:
        candidate = get_snapshot_candidate(args.candidate_id, snapshot_id=args.snapshot_id)
        draft = __import__("asyncio").run(seed_review_draft_from_candidate(candidate, args.card_type))
    print(draft.draft_id)


def seed_group_cmd(args: argparse.Namespace) -> None:
    draft = __import__("asyncio").run(seed_review_group_draft(args.candidate_ids, args.card_type))
    print(draft.draft_id)


def show_cmd(args: argparse.Namespace) -> None:
    draft = next(item for item in list_drafts() if item.draft_id == args.draft_id)
    print(json.dumps(_review_payload(draft), ensure_ascii=False, indent=2))


def update_cmd(args: argparse.Namespace) -> None:
    payload = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
    card = _load_draft(payload)
    update_draft(card.draft_id, card)
    print(card.draft_id)


def publish_cmd(args: argparse.Namespace) -> None:
    card_id, published_count = publish_draft(args.draft_id)
    print(json.dumps({"card_id": card_id, "published_count": published_count}, ensure_ascii=False))


def reject_cmd(args: argparse.Namespace) -> None:
    rejected = save_review_rejection(args.candidate_id, reason=args.reason, note=args.note)
    for draft in list_drafts():
        if draft.candidate_id == args.candidate_id:
            delete_draft(draft.draft_id)
    print(json.dumps(rejected, ensure_ascii=False))


def _load_draft(payload: dict) -> ValidationCardDraft | WritingCardDraft:
    if payload["card_type"] == "validate":
        return ValidationCardDraft.model_validate(payload)
    return WritingCardDraft.model_validate(payload)


def _review_payload(draft: ValidationCardDraft | WritingCardDraft) -> dict:
    return draft.model_dump(mode="json")


if __name__ == "__main__":
    main()
