from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_post_llm_labels_indexes() -> None:
    from app.models.llm_labels import PostLLMLabel

    table = PostLLMLabel.__table__
    indexes = {idx.name: idx for idx in table.indexes}

    assert "ux_post_llm_labels_post_id" in indexes
    assert indexes["ux_post_llm_labels_post_id"].unique is True
    assert "idx_post_llm_labels_created_at" in indexes
    assert "idx_post_llm_labels_text_hash" in indexes


@pytest.mark.asyncio
async def test_comment_llm_labels_indexes() -> None:
    from app.models.llm_labels import CommentLLMLabel

    table = CommentLLMLabel.__table__
    indexes = {idx.name: idx for idx in table.indexes}

    assert "ux_comment_llm_labels_comment_id" in indexes
    assert indexes["ux_comment_llm_labels_comment_id"].unique is True
    assert "idx_comment_llm_labels_created_at" in indexes
    assert "idx_comment_llm_labels_text_hash" in indexes
