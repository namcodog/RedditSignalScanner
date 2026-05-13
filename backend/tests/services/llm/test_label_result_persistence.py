from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.llm.label_result_persistence import (
    LabelResultPersistenceDeps,
    persist_incremental_comment_analysis,
    persist_incremental_post_analysis,
)


@pytest.mark.asyncio
async def test_persist_incremental_post_analysis_upserts_row_and_syncs_terms() -> None:
    upsert_post_rows = AsyncMock(return_value=1)
    sync_terms = AsyncMock(return_value={"pain_point": 1, "feature": 0, "brand": 0})
    session = AsyncMock()
    labeler = SimpleNamespace(model_name="gemini-test", prompt_version="v-test")

    await persist_incremental_post_analysis(
        session=session,
        row_by_id={101: {"text_norm_hash": "hash-101"}},
        labeler=labeler,
        prompt_version="llm-v1",
        item_id=101,
        analysis={"sentiment": 0.1, "entities": {"known": ["shopify"], "new": []}},
        score={"value_score": 8.5, "opportunity_score": 6.0, "business_pool": "core"},
        input_chars=120,
        output_chars=60,
        deps=LabelResultPersistenceDeps(
            upsert_post_label_rows=upsert_post_rows,
            upsert_comment_label_rows=AsyncMock(),
            sync_llm_terms=sync_terms,
        ),
    )

    upsert_post_rows.assert_awaited_once()
    upsert_kwargs = upsert_post_rows.await_args.kwargs
    assert upsert_kwargs["session"] is session
    row = upsert_kwargs["rows"][0]
    assert row["post_id"] == 101
    assert row["text_norm_hash"] == "hash-101"
    assert row["business_pool"] == "core"
    sync_terms.assert_awaited_once_with(
        session,
        analysis={"sentiment": 0.1, "entities": {"known": ["shopify"], "new": []}},
        llm_version="llm-v1",
        prompt_version="v-test",
    )


@pytest.mark.asyncio
async def test_persist_incremental_post_analysis_requires_existing_row() -> None:
    with pytest.raises(KeyError, match="post row not found"):
        await persist_incremental_post_analysis(
            session=AsyncMock(),
            row_by_id={},
            labeler=SimpleNamespace(model_name="gemini-test", prompt_version="v-test"),
            prompt_version="llm-v1",
            item_id=101,
            analysis={"sentiment": 0.1},
            score={"value_score": 8.5, "opportunity_score": 6.0, "business_pool": "core"},
            input_chars=120,
            output_chars=60,
        )


@pytest.mark.asyncio
async def test_persist_incremental_comment_analysis_upserts_row_and_syncs_terms() -> None:
    upsert_comment_rows = AsyncMock(return_value=1)
    sync_terms = AsyncMock(return_value={"pain_point": 0, "feature": 1, "brand": 0})
    session = AsyncMock()
    labeler = SimpleNamespace(model_name="gemini-test", prompt_version="v-test")

    await persist_incremental_comment_analysis(
        session=session,
        labeler=labeler,
        prompt_version="llm-v1",
        item_id=201,
        analysis={"sentiment": -0.2, "aspect_tags": ["pricing"]},
        score={"value_score": 7.5, "opportunity_score": 5.0, "business_pool": "lab"},
        input_chars=90,
        output_chars=30,
        deps=LabelResultPersistenceDeps(
            upsert_post_label_rows=AsyncMock(),
            upsert_comment_label_rows=upsert_comment_rows,
            sync_llm_terms=sync_terms,
        ),
    )

    upsert_comment_rows.assert_awaited_once()
    upsert_kwargs = upsert_comment_rows.await_args.kwargs
    assert upsert_kwargs["session"] is session
    row = upsert_kwargs["rows"][0]
    assert row["comment_id"] == 201
    assert row["business_pool"] == "lab"
    sync_terms.assert_awaited_once_with(
        session,
        analysis={"sentiment": -0.2, "aspect_tags": ["pricing"]},
        llm_version="llm-v1",
        prompt_version="v-test",
    )
