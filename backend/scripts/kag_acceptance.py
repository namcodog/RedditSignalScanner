"""KAG acceptance check: ensure structured outputs are present for example tasks.

Usage:
  cd backend
  export $(cat .env | grep -v '^#' | xargs)
  python scripts/kag_acceptance.py --from-examples --limit 6
  python scripts/kag_acceptance.py --task-id <uuid> --task-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.analysis import Analysis
from app.models.example_library import ExampleLibrary


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _count_non_empty(value: Any) -> int:
    if isinstance(value, list):
        return len([item for item in value if item])
    return 0


def _has_clickable_evidence(items: list[dict[str, Any]]) -> bool:
    for item in items:
        url = str(item.get("url") or "").strip()
        if url:
            return True
    return False


def _validate_knowledge_graph(sources: dict[str, Any]) -> tuple[bool, list[str]]:
    facts_slice = sources.get("facts_slice") or {}
    knowledge_graph = sources.get("knowledge_graph") or facts_slice.get("knowledge_graph")
    if not isinstance(knowledge_graph, dict):
        return False, ["knowledge_graph_missing"]

    communities = _as_list(knowledge_graph.get("communities"))
    pains = _as_list(knowledge_graph.get("pain_points"))
    evidence = _as_list(knowledge_graph.get("evidence"))
    drivers = _as_list(knowledge_graph.get("drivers"))

    issues: list[str] = []
    if not communities:
        issues.append("knowledge_graph.communities.empty")
    if not pains:
        issues.append("knowledge_graph.pain_points.empty")
    if not evidence:
        issues.append("knowledge_graph.evidence.empty")
    if not drivers:
        issues.append("knowledge_graph.drivers.empty")
    if evidence and not _has_clickable_evidence(evidence):
        issues.append("knowledge_graph.evidence.no_clickable_url")

    return not issues, issues


async def _resolve_task_ids(limit: int) -> list[uuid.UUID]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(ExampleLibrary.source_task_id)
            .where(ExampleLibrary.is_active == True)
            .where(ExampleLibrary.source_task_id.is_not(None))
            .order_by(ExampleLibrary.updated_at.desc())
            .limit(limit)
        )
        return [row[0] for row in result.all() if row[0] is not None]


async def _check_tasks(task_ids: list[uuid.UUID]) -> int:
    if not task_ids:
        print("❌ 未找到可验收的 task_id")
        return 1

    failures = 0
    async with SessionFactory() as session:
        result = await session.execute(
            select(Analysis).where(Analysis.task_id.in_(task_ids))
        )
        rows = {row.Analysis.task_id: row.Analysis for row in result.all()}

    for task_id in task_ids:
        analysis = rows.get(task_id)
        if analysis is None:
            print(f"❌ task {task_id} 没有 analysis 记录")
            failures += 1
            continue

        sources = analysis.sources or {}
        tier = sources.get("report_tier")
        if tier in {"C_scouting", "X_blocked"}:
            print(f"⚠️ task {task_id} 报告降级({tier})，不计入通过")
            failures += 1
            continue

        hybrid_used = sources.get("hybrid_posts_used")
        if hybrid_used is None:
            print(f"❌ task {task_id} 缺少 sources.hybrid_posts_used")
            failures += 1

        ok, issues = _validate_knowledge_graph(sources)
        if ok:
            print(f"✅ task {task_id} knowledge_graph OK")
        else:
            print(f"❌ task {task_id} knowledge_graph 问题: {', '.join(issues)}")
            failures += 1

    return failures


async def _run(args: argparse.Namespace) -> int:
    task_ids = [uuid.UUID(tid) for tid in args.task_id]
    if not task_ids and args.from_examples:
        task_ids = await _resolve_task_ids(args.limit)

    return await _check_tasks(task_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="KAG acceptance check")
    parser.add_argument("--task-id", action="append", default=[], help="task UUID")
    parser.add_argument("--from-examples", action="store_true", help="use example_library")
    parser.add_argument("--limit", type=int, default=6, help="example count")
    args = parser.parse_args()

    failures = asyncio.run(_run(args))
    if failures:
        raise SystemExit(1)
    print("✅ KAG 验收通过")


if __name__ == "__main__":
    main()
