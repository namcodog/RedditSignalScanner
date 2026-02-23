#!/usr/bin/env python3
"""T1 数据覆盖盘点：社区数、12个月帖子/评论、标签/实体覆盖率."""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionFactory


async def main() -> None:
    since = datetime.now(timezone.utc) - timedelta(days=365)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since_utc": since.isoformat(),
        "t1_communities": [],
        "posts": {},
        "comments": {},
        "labels": {},
        "entities": {},
    }
    async with SessionFactory() as session:
        # T1 active communities
        rows = await session.execute(
            text(
                "SELECT lower(name) AS name FROM community_pool "
                "WHERE tier='high' AND is_active=true AND deleted_at IS NULL ORDER BY name"
            )
        )
        # Do not strip r/ prefix, as posts_raw/comments store it
        subs = [r.name for r in rows.fetchall()]
        output["t1_communities"] = subs

        # Posts/Comments counts
        params = {"since": since, "subs": subs or [""], "has_subs": bool(subs)}
        posts_rows = await session.execute(
            text(
                """
                SELECT COUNT(*) AS cnt FROM posts_raw
                WHERE is_current = true AND created_at >= :since
                  AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
                """
            ),
            params,
        )
        output["posts"]["last_12m"] = int(posts_rows.scalar_one() or 0)

        comments_rows = await session.execute(
            text(
                """
                SELECT COUNT(*) AS cnt FROM comments
                WHERE created_utc >= :since
                  AND (:has_subs = FALSE OR lower(subreddit) = ANY(:subs))
                """
            ),
            params,
        )
        output["comments"]["last_12m"] = int(comments_rows.scalar_one() or 0)

        # Labels coverage
        label_rows = await session.execute(
            text(
                """
                SELECT
                    SUM(CASE WHEN category = 'pain' THEN 1 ELSE 0 END) AS pain,
                    SUM(CASE WHEN category = 'solution' THEN 1 ELSE 0 END) AS solution,
                    COUNT(*) AS total
                FROM content_labels cl
                JOIN comments c ON c.id = cl.content_id
                WHERE cl.content_type='comment'
                  AND c.created_utc >= :since
                  AND (:has_subs = FALSE OR lower(c.subreddit) = ANY(:subs))
                """
            ),
            params,
        )
        row = label_rows.first()
        if row:
            output["labels"] = {
                "pain": int(row.pain or 0),
                "solution": int(row.solution or 0),
                "total": int(row.total or 0),
            }

        # Entities coverage
        ent_rows = await session.execute(
            text(
                """
                SELECT COUNT(*) AS total FROM content_entities ce
                JOIN comments c ON c.id = ce.content_id
                WHERE ce.content_type='comment'
                  AND c.created_utc >= :since
                  AND (:has_subs = FALSE OR lower(c.subreddit) = ANY(:subs))
                """
            ),
            params,
        )
        output["entities"]["total"] = int(ent_rows.scalar_one() or 0)

        # Embeddings coverage (Phase 5)
        embed_rows = await session.execute(
            text("SELECT COUNT(*) FROM post_embeddings")
        )
        output["embeddings"] = {"total": int(embed_rows.scalar_one() or 0)}

    out_path = Path("reports/local-acceptance/t1-data-audit.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ T1 data audit written to {out_path}")


if __name__ == "__main__":
    from app.core.preflight import run_preflight_checks
    if not run_preflight_checks(strict_llm=False):
        exit(1)
    asyncio.run(main())
