"""Threshold optimisation utilities for labeled dataset evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Tuple

import pandas as pd
import yaml

from app.services.analysis.opportunity_scorer import OpportunityScorer


@dataclass(frozen=True)
class ThresholdEvaluation:
    threshold: float
    precision_at_50: float
    f1_score: float


def score_posts(
    labeled_df: pd.DataFrame,
    *,
    scorer: object | None = None,
) -> pd.DataFrame:
    """Attach predicted opportunity scores to the labeled dataset."""
    if "title" not in labeled_df.columns or "body" not in labeled_df.columns:
        raise ValueError("labeled_df must include 'title' and 'body' columns.")

    effective_scorer = scorer or OpportunityScorer()
    scored_df = labeled_df.copy()

    def _score_row(row: pd.Series[Any]) -> float:
        text = f"{row.get('title', '')} {row.get('body', '')}".strip()
        result = effective_scorer.score(text)  # type: ignore[attr-defined]
        base_score = result.base_score
        return float(max(0.0, min(1.0, base_score)))

    scored_df["predicted_score"] = scored_df.apply(_score_row, axis=1)
    return scored_df


def calculate_precision_at_k(
    scored_df: pd.DataFrame,
    *,
    threshold: float,
    k: int = 50,
) -> float:
    """Compute Precision@K for the given threshold."""
    if "predicted_score" not in scored_df.columns or "label" not in scored_df.columns:
        raise ValueError("scored_df must include 'predicted_score' and 'label'.")
    if k <= 0:
        raise ValueError("k must be positive.")

    sorted_df = scored_df.sort_values("predicted_score", ascending=False)
    top_k = sorted_df.head(min(k, len(sorted_df)))
    if top_k.empty:
        return 0.0

    predicted_positive = top_k["predicted_score"] >= threshold
    positive_count = int(predicted_positive.sum())
    if positive_count == 0:
        return 0.0

    labels = top_k["label"].astype(str).str.lower()
    true_positive = (labels == "opportunity") & predicted_positive
    return float(true_positive.sum() / positive_count)


def calculate_f1_score(scored_df: pd.DataFrame, *, threshold: float) -> float:
    """Compute F1 score for the given threshold."""
    if "predicted_score" not in scored_df.columns or "label" not in scored_df.columns:
        raise ValueError("scored_df must include 'predicted_score' and 'label'.")

    labels = scored_df["label"].astype(str).str.lower()
    actual_positive = labels == "opportunity"
    predicted_positive = scored_df["predicted_score"] >= threshold
    true_positive = predicted_positive & actual_positive

    precision_denominator = int(predicted_positive.sum())
    precision = (
        float(true_positive.sum() / precision_denominator)
        if precision_denominator
        else 0.0
    )

    recall_denominator = int(actual_positive.sum())
    recall = (
        float(true_positive.sum() / recall_denominator)
        if recall_denominator
        else 0.0
    )

    if precision + recall == 0.0:
        return 0.0
    return float((2 * precision * recall) / (precision + recall))


def grid_search_threshold(
    labeled_df: pd.DataFrame,
    *,
    thresholds: Iterable[float],
    scorer: object | None = None,
) -> List[ThresholdEvaluation]:
    """Execute grid search returning evaluation metrics for each threshold."""
    threshold_candidates = sorted({float(value) for value in thresholds})
    if not threshold_candidates:
        raise ValueError("thresholds must contain at least one value.")

    scored_df = score_posts(labeled_df, scorer=scorer)
    evaluations: List[ThresholdEvaluation] = []

    for threshold in threshold_candidates:
        precision = calculate_precision_at_k(scored_df, threshold=threshold, k=50)
        f1 = calculate_f1_score(scored_df, threshold=threshold)
        evaluations.append(
            ThresholdEvaluation(
                threshold=threshold,
                precision_at_50=precision,
                f1_score=f1,
            )
        )
    return evaluations


def select_optimal_threshold(
    evaluations: Iterable[ThresholdEvaluation],
    *,
    precision_floor: float = 0.6,
) -> ThresholdEvaluation:
    """Select the best threshold given Precision@50 and F1 constraints."""
    evaluations_list = list(evaluations)
    if not evaluations_list:
        raise ValueError("evaluations must not be empty.")

    eligible = [
        item for item in evaluations_list if item.precision_at_50 >= precision_floor
    ]
    if eligible:
        return max(
            eligible,
            key=lambda item: (item.f1_score, item.precision_at_50, -item.threshold),
        )

    return max(
        evaluations_list,
        key=lambda item: (item.precision_at_50, item.f1_score, -item.threshold),
    )


def save_grid_search_results(
    evaluations: Iterable[ThresholdEvaluation],
    output_path: Path,
) -> None:
    """Persist grid search results to a CSV report."""
    rows = [
        {
            "threshold": item.threshold,
            "precision_at_50": item.precision_at_50,
            "f1_score": item.f1_score,
        }
        for item in evaluations
    ]
    df = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


def update_threshold_config(threshold: float, *, config_path: Path) -> None:
    """Write the selected threshold to the YAML configuration."""
    if threshold <= 0 or threshold >= 1:
        raise ValueError("threshold must be within (0, 1).")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, float] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
            if isinstance(loaded, dict):
                payload.update(loaded)

    payload["opportunity_threshold"] = float(threshold)
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=True, allow_unicode=True)
