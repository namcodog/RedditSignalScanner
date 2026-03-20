from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from app.services.llm import legacy_label_persistence as mod


@pytest.mark.asyncio
async def test_upsert_legacy_post_label_builds_row_and_upserts(monkeypatch: pytest.MonkeyPatch) -> None:
    build_row = Mock(return_value={"post_id": 1})
    upsert_rows = AsyncMock()
    monkeypatch.setattr(mod, "build_post_label_row", build_row)
    monkeypatch.setattr(mod, "upsert_post_label_rows", upsert_rows)

    await mod.upsert_legacy_post_label(
        session=object(),
        post_id=1,
        text_norm_hash="hash",
        llm_version="legacy",
        model_name="legacy",
        prompt_version="legacy_v2",
        analysis={"pain_tags": ["fees"]},
        score={"value_score": 8.0},
        input_chars=0,
        output_chars=0,
    )

    build_row.assert_called_once()
    upsert_rows.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_legacy_comment_label_builds_row_and_upserts(monkeypatch: pytest.MonkeyPatch) -> None:
    build_row = Mock(return_value={"comment_id": 2})
    upsert_rows = AsyncMock()
    monkeypatch.setattr(mod, "build_comment_label_row", build_row)
    monkeypatch.setattr(mod, "upsert_comment_label_rows", upsert_rows)

    await mod.upsert_legacy_comment_label(
        session=object(),
        comment_id=2,
        llm_version="legacy",
        model_name="legacy",
        prompt_version="legacy_v2",
        analysis={"aspect_tags": ["pricing"]},
        score={"value_score": 7.0},
        input_chars=0,
        output_chars=0,
    )

    build_row.assert_called_once()
    upsert_rows.assert_awaited_once()
