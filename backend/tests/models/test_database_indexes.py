from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app.core.config import Settings
from app.models.community_pool import (
    CommunityPool,
    PendingCommunity,
)
from app.models.posts_storage import PostHot


def _index_names(table):
    return {index.name: index for index in table.indexes}


def test_pending_community_uuid_columns() -> None:
    table = PendingCommunity.__table__
    discovered_type = table.c.discovered_from_task_id.type
    reviewed_type = table.c.reviewed_by.type

    assert isinstance(discovered_type, postgresql.UUID)
    assert isinstance(reviewed_type, postgresql.UUID)


def test_pending_community_indexes_present() -> None:
    indexes = _index_names(PendingCommunity.__table__)
    assert "idx_pending_communities_task_id" in indexes
    assert "idx_pending_communities_reviewed_by" in indexes
    assert "idx_pending_communities_status" in indexes
    assert "idx_pending_communities_deleted_at" in indexes


# 测试已删除: CommunityImportHistory 表已移除（功能孤岛清理）
# def test_community_import_history_indexes_present() -> None:
#     ...


def test_community_pool_gin_indexes() -> None:
    indexes = _index_names(CommunityPool.__table__)
    categories_idx = indexes.get("idx_community_pool_categories_gin")
    keywords_idx = indexes.get("idx_community_pool_keywords_gin")
    deleted_idx = indexes.get("idx_community_pool_deleted_at")

    assert categories_idx is not None
    assert keywords_idx is not None
    assert categories_idx.dialect_kwargs.get("postgresql_using") == "gin"
    assert keywords_idx.dialect_kwargs.get("postgresql_using") == "gin"
    assert deleted_idx is not None


def test_posts_hot_metadata_gin_index() -> None:
    indexes = _index_names(PostHot.__table__)
    metadata_idx = indexes.get("idx_posts_hot_metadata_gin")

    assert metadata_idx is not None
    assert metadata_idx.dialect_kwargs.get("postgresql_using") == "gin"


def test_settings_default_database_name() -> None:
    settings = Settings()
    assert "reddit_signal_scanner" in settings.database_url


def test_audit_and_soft_delete_columns_present() -> None:
    pool_columns = CommunityPool.__table__.c
    assert "created_by" in pool_columns
    assert "updated_by" in pool_columns
    assert "deleted_at" in pool_columns
    assert "deleted_by" in pool_columns
