from __future__ import annotations

from app.services.analysis.analysis_signal_support import (
    build_data_lineage,
    extract_business_signals_from_labels,
    fetch_post_embeddings,
    looks_like_reddit_post_id,
    merge_business_signals_with_heuristics,
    parse_embedding_value,
    truncate_target_ids,
)
from app.services.analysis.signal_extraction import (
    BusinessSignals,
    CompetitorSignal,
    OpportunitySignal,
    PainPointSignal,
    SolutionSignal,
)


class _FakeMappingResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "_FakeMappingResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class _FakeSession:
    def __init__(self, queue: list[object]) -> None:
        self._queue = queue

    async def execute(self, *_args: object, **_kwargs: object) -> object:
        return self._queue.pop(0)


class _FakeSessionContext:
    def __init__(self, queue: list[object]) -> None:
        self._queue = queue

    async def __aenter__(self) -> _FakeSession:
        return _FakeSession(self._queue)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def test_truncate_target_ids_and_lineage_contract() -> None:
    trimmed, total, truncated = truncate_target_ids(
        ["a1", "a2", "a3"],
        max_items=2,
    )

    lineage = build_data_lineage(
        source_range={"posts": 3, "comments": 2},
        coverage={"coverage_ratio": 0.8},
        remediation_actions=[
            {
                "crawl_run_id": "run-1",
                "target_ids": ["a1", "a2"],
                "target_ids_total": 3,
                "target_ids_truncated": True,
            }
        ],
    )

    assert (trimmed, total, truncated) == (["a1", "a2"], 3, True)
    assert lineage["crawler_run_ids"] == ["run-1"]
    assert lineage["target_ids"] == ["a1", "a2"]
    assert lineage["target_ids_total"] == 3
    assert lineage["target_ids_truncated"] is True


def test_parse_embedding_value_and_post_id_guard() -> None:
    assert parse_embedding_value("[1, 2.5]") == [1.0, 2.5]
    assert parse_embedding_value("['1', '2']") == [1.0, 2.0]
    assert parse_embedding_value("oops") is None
    assert looks_like_reddit_post_id("t3_1abcde") is True
    assert looks_like_reddit_post_id("r/foo/bar") is False


async def test_fetch_post_embeddings_and_extract_business_signals() -> None:
    embedding_queue = [
        _FakeMappingResult(
            [
                {"post_id": 11, "embedding": "[0.1, 0.2]"},
                {"post_id": 12, "embedding": None},
            ]
        )
    ]
    embeddings = await fetch_post_embeddings(
        _FakeSession(embedding_queue),
        [{"db_id": 11}, {"db_id": 12}, {"db_id": "bad"}],
        model_name="demo-model",
    )

    signal_queue = [
        _FakeMappingResult(
            [
                {
                    "category": "pain",
                    "aspect": "payout delay",
                    "count": 4,
                    "avg_sentiment": -0.7,
                    "sample_post_ids": [11, 12],
                },
                {
                    "category": "intent",
                    "aspect": "w2c_fast_checkout",
                    "count": 2,
                    "avg_sentiment": 0.0,
                    "sample_post_ids": [11],
                },
                {
                    "category": "solution",
                    "aspect": "checkout simplification",
                    "count": 3,
                    "avg_sentiment": 0.2,
                    "sample_post_ids": [12],
                },
            ]
        ),
        _FakeMappingResult(
            [
                {
                    "entity_name": "PayPal",
                    "mentions": 3,
                    "sample_post_ids": [11],
                }
            ]
        ),
    ]
    signals = await extract_business_signals_from_labels(
        [11, 12],
        session_factory=lambda: _FakeSessionContext(signal_queue),
    )

    assert embeddings == {"11": [0.1, 0.2]}
    assert signals is not None
    assert len(signals.pain_points) == 1
    assert signals.pain_points[0].description == "payout delay相关痛点"
    assert len(signals.competitors) == 1
    assert signals.competitors[0].name == "PayPal"
    assert len(signals.opportunities) == 2
    assert len(signals.solutions) == 1
    assert signals.solutions[0].description == "checkout simplification 解决方案"


def test_merge_business_signals_with_heuristics_supplements_sparse_solution_layer() -> None:
    primary = BusinessSignals(
        pain_points=[
            PainPointSignal(
                description="支付相关痛点",
                frequency=3,
                sentiment=-0.4,
                keywords=["payment"],
                source_posts=["1"],
                relevance=1.0,
            )
        ],
        competitors=[
            CompetitorSignal(
                name="Shopify",
                mention_count=2,
                sentiment=0.0,
                context_snippets=[],
                source_posts=["1"],
                relevance=1.0,
            )
        ],
        opportunities=[
            OpportunitySignal(
                description="checkout 相关 Feature Gap",
                demand_score=0.7,
                unmet_need="用户期待 checkout 方向的解决方案",
                potential_users=3,
                source_posts=["1"],
                relevance=0.8,
                keywords=["checkout"],
            )
        ],
        solutions=[],
        ps_ratio=1.2,
    )
    heuristic = BusinessSignals(
        pain_points=[],
        competitors=[],
        opportunities=[
            OpportunitySignal(
                description="简化支付流程",
                demand_score=0.7,
                unmet_need="减少支付阻塞",
                potential_users=5,
                source_posts=["2"],
                relevance=0.8,
                keywords=["payment"],
            )
        ],
        solutions=[
            SolutionSignal(
                description="简化支付流程",
                frequency=2,
                sentiment=0.1,
                source_posts=["2"],
                relevance=0.9,
            ),
            SolutionSignal(
                description="增加信任徽章",
                frequency=1,
                sentiment=0.0,
                source_posts=["3"],
                relevance=0.7,
            ),
        ],
        ps_ratio=0.8,
    )

    merged = merge_business_signals_with_heuristics(primary, heuristic)

    assert len(merged.pain_points) == 1
    assert merged.pain_points[0].description == "支付相关痛点"
    assert len(merged.competitors) == 1
    assert len(merged.opportunities) == 2
    assert len(merged.solutions) == 2
