from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.db.session import SessionFactory
from app.services.community.community_recommendation_audit import (
    render_audit_markdown,
)
from app.services.community.community_recommendation_markdown import render_markdown
from app.services.community.community_recommendation_preview import (
    CommunityActivitySnapshot,
)
from app.services.community.community_recommendation_service import (
    CommunityRecommendationReport,
    build_community_recommendation_report,
)

DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "reports" / "community-recommendation" / "preview.json"
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "community-recommendation" / "preview.md"
DEFAULT_AUDIT_JSON_OUTPUT = PROJECT_ROOT / "reports" / "community-recommendation" / "audit.json"
DEFAULT_AUDIT_MD_OUTPUT = PROJECT_ROOT / "reports" / "community-recommendation" / "audit.md"


def load_activity_snapshots(path: Path | None) -> tuple[CommunityActivitySnapshot, ...]:
    if path is None:
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("activity input must be a JSON list")
    snapshots: list[CommunityActivitySnapshot] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("activity input items must be JSON objects")
        community = item.get("community")
        recent_posts = item.get("recent_posts_15d")
        latest_activity = item.get("latest_activity_at")
        source = item.get("source") or "activity_input"
        if not isinstance(community, str) or not isinstance(recent_posts, int):
            raise ValueError("activity input requires community and recent_posts_15d")
        snapshots.append(
            CommunityActivitySnapshot(
                community=community,
                recent_posts_15d=recent_posts,
                latest_activity_at=str(latest_activity) if latest_activity else None,
                source=str(source),
            )
        )
    return tuple(snapshots)


async def build(
    *,
    tag_limit: int,
    community_limit: int,
    activity_input: Path | None = None,
) -> CommunityRecommendationReport:
    async with SessionFactory() as session:
        return await build_community_recommendation_report(
            session,
            tag_limit=tag_limit,
            community_limit=community_limit,
            activity_snapshots=load_activity_snapshots(activity_input),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a read-only community recommendation preview.")
    parser.add_argument("--tag-limit", type=int, default=10)
    parser.add_argument("--community-limit", type=int, default=20)
    parser.add_argument("--activity-input", type=Path, default=None)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--audit-json-output", type=Path, default=DEFAULT_AUDIT_JSON_OUTPUT)
    parser.add_argument("--audit-md-output", type=Path, default=DEFAULT_AUDIT_MD_OUTPUT)
    return parser.parse_args()


def write_outputs(args: argparse.Namespace, report: CommunityRecommendationReport) -> None:
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report.preview_payload(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    args.md_output.write_text(render_markdown(report.preview), encoding="utf-8")
    args.audit_json_output.write_text(
        json.dumps(report.audit_payload(), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    args.audit_md_output.write_text(render_audit_markdown(report.audit), encoding="utf-8")


def main() -> None:
    args = parse_args()
    report = asyncio.run(
        build(
            tag_limit=args.tag_limit,
            community_limit=args.community_limit,
            activity_input=args.activity_input,
        )
    )
    write_outputs(args, report)
    print(
        json.dumps(
            {
                **report.summary,
                "json_output": str(args.json_output),
                "md_output": str(args.md_output),
                "audit_json_output": str(args.audit_json_output),
                "audit_md_output": str(args.audit_md_output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
