"""
验证冷/热存储结构完全由 Alembic 管理
"""
from __future__ import annotations

from pathlib import Path


def test_cold_hot_storage_is_controlled_by_alembic() -> None:
    root = Path(__file__).resolve().parents[3]
    manual_sql = root / "backend/migrations/001_cold_hot_storage.sql"
    assert not manual_sql.exists(), "手工 SQL 迁移仍存在，应迁移到 Alembic"

    versions_dir = root / "backend/alembic/versions"
    version_files = list(versions_dir.glob("*.py"))
    assert version_files, "缺少 Alembic 版本文件"

    contents = [path.read_text(encoding="utf-8") for path in version_files]
    posts_raw_covered = any(
        "op.create_table" in text and "posts_raw" in text for text in contents
    )
    posts_hot_covered = any(
        "op.create_table" in text and "posts_hot" in text for text in contents
    )

    assert posts_raw_covered, "Alembic 版本中未定义 posts_raw 表结构"
    assert posts_hot_covered, "Alembic 版本中未定义 posts_hot 表结构"
