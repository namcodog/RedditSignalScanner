from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_saturation_matrix_basic(db_session) -> None:
    """
    基础饱和度：r/A 社区有 5 篇帖子，其中 3 篇提到 BrandX，BrandY 无提及。
    期望：
      - BrandX 饱和度约 0.6（3/5）
      - BrandY 饱和度约 0.0
      - overall_saturation 在 0~1 之间
    """
    await db_session.execute(text("DELETE FROM posts_hot"))
    await db_session.execute(text("DELETE FROM content_entities"))

    # 插入 5 篇 posts_hot
    for i in range(5):
        await db_session.execute(
            text(
                """
                INSERT INTO posts_hot (id, source, source_post_id, created_at, expires_at, title, body, subreddit, score, num_comments, metadata)
                VALUES (:id, 'reddit', :pid, NOW(), NOW() + INTERVAL '1 day', :title, :body, 'r/A', 1, 0, '{}'::jsonb)
                """
            ),
            {"id": 8000 + i, "pid": f"pA{i}", "title": f"t{i}", "body": f"b{i}"},
        )

    # 在 3 篇帖子上标注 BrandX 实体
    for pid in (8000, 8001, 8002):
        await db_session.execute(
            text(
                """
                INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                VALUES ('post', :cid, 'BrandX', 'brand', 1)
                """
            ),
            {"cid": pid},
        )

    await db_session.commit()

    import importlib
    mod = importlib.import_module("app.services.analysis.saturation_matrix")
    svc = mod.SaturationMatrix()

    rows = await svc.compute(db_session, communities=["r/A"], brands=["BrandX", "BrandY"])
    assert isinstance(rows, list) and len(rows) == 1
    row = rows[0]
    assert getattr(row, "community") == "r/A"
    brands = {b.brand: b for b in getattr(row, "brands")}
    assert "BrandX" in brands and "BrandY" in brands
    bx = brands["BrandX"].saturation
    by = brands["BrandY"].saturation
    assert 0.5 <= bx <= 0.7  # 约 0.6 容忍浮动
    assert 0.0 <= by <= 0.05
    assert 0.0 <= float(getattr(row, "overall_saturation", 0.0)) <= 1.0


@pytest.mark.asyncio
async def test_saturation_matrix_classification_thresholds(db_session) -> None:
    """
    阈值分类：
      - r/T1: BrandA 提及 8/10 → 高饱和
      - r/T2: BrandB 提及 5/10 → 中等
      - r/T3: BrandC 提及 1/10 → 机会窗口
    """
    await db_session.execute(text("DELETE FROM posts_hot"))
    await db_session.execute(text("DELETE FROM content_entities"))

    async def seed(sub: str, brand: str, total: int, hits: int) -> None:
        base = 8100 if sub == "r/T1" else (8200 if sub == "r/T2" else 8300)
        for i in range(total):
            pid = base + i
            await db_session.execute(
                text(
                    """
                    INSERT INTO posts_hot (id, source, source_post_id, created_at, expires_at, title, body, subreddit, score, num_comments, metadata)
                    VALUES (:id, 'reddit', :pid, NOW(), NOW() + INTERVAL '1 day', :title, :body, :sub, 1, 0, '{}'::jsonb)
                    """
                ),
                {"id": pid, "pid": f"p_{sub}_{i}", "title": "t", "body": "b", "sub": sub},
            )
        # 标注命中
        for i in range(hits):
            pid = base + i
            await db_session.execute(
                text(
                    """
                    INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                    VALUES ('post', :cid, :brand, 'brand', 1)
                    """
                ),
                {"cid": pid, "brand": brand},
            )

    await seed("r/T1", "BrandA", total=10, hits=8)  # 0.8
    await seed("r/T2", "BrandB", total=10, hits=5)  # 0.5
    await seed("r/T3", "BrandC", total=10, hits=1)  # 0.1
    await db_session.commit()

    import importlib
    mod = importlib.import_module("app.services.analysis.saturation_matrix")
    svc = mod.SaturationMatrix()

    out = await svc.compute(db_session, ["r/T1", "r/T2", "r/T3"], ["BrandA", "BrandB", "BrandC"])
    assert len(out) == 3
    status_map = {}
    for row in out:
        m = {b.brand: b.status for b in getattr(row, "brands")}
        status_map[row.community] = m

    assert status_map["r/T1"]["BrandA"] in ("高饱和", "中等")  # 容忍实现细节，但应非“机会窗口”
    assert status_map["r/T2"]["BrandB"] in ("中等", "高饱和")
    assert status_map["r/T3"]["BrandC"] in ("机会窗口", "中等")


@pytest.mark.asyncio
async def test_saturation_opportunity_windows(db_session) -> None:
    """
    机会窗口：品牌在某些社区饱和度 < 0.2，应作为优先切入点返回。
    - BrandX: r/A=0.1 (1/10), r/B=0.0 (0/10), r/C=0.8 (8/10) → 机会窗口包含 r/B, r/A
    - BrandY: r/A=0.7, r/B=0.0, r/C=0.0 → 机会窗口包含 r/B, r/C
    """
    await db_session.execute(text("DELETE FROM posts_hot"))
    await db_session.execute(text("DELETE FROM content_entities"))

    async def seed_posts(sub: str, total: int) -> list[int]:
        base = {
            "r/A": 8400,
            "r/B": 8500,
            "r/C": 8600,
        }[sub]
        ids: list[int] = []
        for i in range(total):
            pid = base + i
            ids.append(pid)
            await db_session.execute(
                text(
                    """
                    INSERT INTO posts_hot (id, source, source_post_id, created_at, expires_at, title, body, subreddit, score, num_comments, metadata)
                    VALUES (:id, 'reddit', :pid, NOW(), NOW() + INTERVAL '1 day', :title, :body, :sub, 1, 0, '{}'::jsonb)
                    """
                ),
                {"id": pid, "pid": f"p_{sub}_{i}", "title": "t", "body": "b", "sub": sub},
            )
        return ids

    ids_a = await seed_posts("r/A", 10)
    ids_b = await seed_posts("r/B", 10)
    ids_c = await seed_posts("r/C", 10)

    # BrandX: 1/10 in r/A, 0/10 in r/B, 8/10 in r/C
    for pid in ids_a[:1]:
        await db_session.execute(text("INSERT INTO content_entities (content_type, content_id, entity, entity_type, count) VALUES ('post', :cid, 'BrandX', 'brand', 1)"), {"cid": pid})
    for pid in ids_c[:8]:
        await db_session.execute(text("INSERT INTO content_entities (content_type, content_id, entity, entity_type, count) VALUES ('post', :cid, 'BrandX', 'brand', 1)"), {"cid": pid})

    # BrandY: 7/10 in r/A
    for pid in ids_a[:7]:
        await db_session.execute(text("INSERT INTO content_entities (content_type, content_id, entity, entity_type, count) VALUES ('post', :cid, 'BrandY', 'brand', 1)"), {"cid": pid})

    await db_session.commit()

    import importlib
    mod = importlib.import_module("app.services.analysis.saturation_matrix")
    svc = mod.SaturationMatrix()
    opp = await svc.compute_opportunity_windows(
        db_session,
        communities=["r/A", "r/B", "r/C"],
        brands=["BrandX", "BrandY"],
        low_threshold=0.2,
        top_n=2,
    )

    assert "BrandX" in opp and "BrandY" in opp
    bx = [row["community"] for row in opp["BrandX"]]
    by = [row["community"] for row in opp["BrandY"]]
    assert set(bx) == {"r/B", "r/A"}
    assert set(by) == {"r/B", "r/C"}
