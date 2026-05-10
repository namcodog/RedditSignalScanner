from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.analysis.t1_clustering import _fetch_pain_comments


class _Rows:
    def __init__(self, rows):
        self._rows = list(rows)

    def fetchall(self):
        return list(self._rows)


class _Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def execute(self, stmt, params):
        sql = getattr(stmt, "text", str(stmt))
        self.calls.append((sql, dict(params)))
        return _Rows(
            [
                SimpleNamespace(
                    aspect="price",
                    body="This pricing setup keeps getting more expensive every month.",
                ),
                SimpleNamespace(aspect="price", body="Too short"),
            ]
        )


@pytest.mark.asyncio
async def test_fetch_pain_comments_reads_semantic_observation() -> None:
    session = _Session()

    buckets = await _fetch_pain_comments(
        session,
        subs=["AItools"],
        since_dt=datetime(2026, 3, 1, tzinfo=timezone.utc),
        sample_per_aspect=3,
    )

    assert buckets == {
        "price": ["This pricing setup keeps getting more expensive every month."]
    }
    assert len(session.calls) == 1
    sql, params = session.calls[0]
    assert "semantic_observation" in sql
    assert "content_labels" not in sql
    assert params["subs"] == ["r/aitools"]
