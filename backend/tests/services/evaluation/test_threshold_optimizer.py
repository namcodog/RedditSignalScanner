from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, List

import pandas as pd
import pytest

from app.services.evaluation.threshold_optimizer import (
    ThresholdEvaluation,
    calculate_f1_score,
    calculate_precision_at_k,
    grid_search_threshold,
    save_grid_search_results,
    score_posts,
    select_optimal_threshold,
    update_threshold_config,
)


class StubScorer:
    """Deterministic scorer used for testing threshold utilities."""

    def score(self, text: str) -> SimpleNamespace:
        base = 0.9 if "opportunity" in text.lower() else 0.2
        return SimpleNamespace(base_score=base)


def _make_labeled_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "post_id": "a",
                "title": "Great opportunity in fintech",
                "body": "Looking for banking automation tools",
                "label": "opportunity",
            },
            {
                "post_id": "b",
                "title": "General discussion thread",
                "body": "Just chatting",
                "label": "non-opportunity",
            },
            {
                "post_id": "c",
                "title": "Big opportunity in SaaS",
                "body": "Need better onboarding",
                "label": "opportunity",
            },
            {
                "post_id": "d",
                "title": "Question about pricing",
                "body": "Does anyone know alternatives?",
                "label": "non-opportunity",
            },
        ]
    )


def test_score_posts_adds_prediction_column() -> None:
    labeled = _make_labeled_dataframe()
    scored = score_posts(labeled, scorer=StubScorer())
    assert "predicted_score" in scored.columns
    assert scored["predicted_score"].between(0, 1).all()


def test_precision_at_k_handles_small_dataset() -> None:
    labeled = _make_labeled_dataframe()
    scored = score_posts(labeled, scorer=StubScorer())
    precision = calculate_precision_at_k(scored, threshold=0.5, k=50)
    assert 0.0 <= precision <= 1.0
    assert precision == pytest.approx(1.0, rel=1e-3)


def test_calculate_f1_score_balances_precision_and_recall() -> None:
    labeled = _make_labeled_dataframe()
    scored = score_posts(labeled, scorer=StubScorer())
    f1 = calculate_f1_score(scored, threshold=0.5)
    assert 0.0 <= f1 <= 1.0
    assert f1 == pytest.approx(1.0, rel=1e-3)


def test_grid_search_threshold_evaluates_each_candidate() -> None:
    labeled = _make_labeled_dataframe()
    evaluations = grid_search_threshold(
        labeled,
        thresholds=[0.3, 0.5, 0.7],
        scorer=StubScorer(),
    )
    assert len(evaluations) == 3
    assert all(isinstance(item, ThresholdEvaluation) for item in evaluations)


def test_select_optimal_threshold_prioritises_precision() -> None:
    evaluations: List[ThresholdEvaluation] = [
        ThresholdEvaluation(threshold=0.3, precision_at_50=0.55, f1_score=0.7),
        ThresholdEvaluation(threshold=0.5, precision_at_50=0.62, f1_score=0.65),
        ThresholdEvaluation(threshold=0.7, precision_at_50=0.7, f1_score=0.6),
    ]
    chosen = select_optimal_threshold(evaluations, precision_floor=0.6)
    assert chosen.threshold == 0.5


def test_save_results_and_update_config(tmp_path: Path) -> None:
    evaluations: Iterable[ThresholdEvaluation] = [
        ThresholdEvaluation(threshold=0.3, precision_at_50=0.55, f1_score=0.65),
        ThresholdEvaluation(threshold=0.5, precision_at_50=0.62, f1_score=0.70),
    ]
    output_csv = tmp_path / "thresholds.csv"
    save_grid_search_results(evaluations, output_csv)
    assert output_csv.exists()
    content = output_csv.read_text(encoding="utf-8")
    assert "precision_at_50" in content

    config_path = tmp_path / "thresholds.yaml"
    update_threshold_config(0.56, config_path=config_path)
    data = config_path.read_text(encoding="utf-8")
    assert "opportunity_threshold: 0.56" in data
