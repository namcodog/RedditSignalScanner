"""
Validation helpers for labeled datasets generated during Phase 3.
"""

from __future__ import annotations

from typing import Iterable, Set

import pandas as pd

from .sampler import SAMPLE_COLUMNS

VALID_LABELS: Set[str] = {"opportunity", "non-opportunity"}
VALID_STRENGTHS: Set[str] = {"strong", "medium", "weak"}


def _validate_required_columns(labeled_df: pd.DataFrame) -> None:
    missing = [column for column in SAMPLE_COLUMNS if column not in labeled_df.columns]
    if missing:
        raise ValueError(f"缺少必要字段: {', '.join(missing)}")


def _fetch_invalid_entries(values: Iterable[str | float], valid_set: Set[str]) -> Set[str]:
    invalid: Set[str] = set()
    for value in values:
        if isinstance(value, float) and pd.isna(value):
            invalid.add("nan")
            continue
        text = str(value).strip()
        if text and text.lower() in valid_set:
            continue
        invalid.add(text)
    return {val for val in invalid if val}


def validate_labels(
    labeled_df: pd.DataFrame,
    *,
    expected_count: int = 500,
) -> None:
    """Ensure the labeled dataset is complete and consistent."""
    if expected_count <= 0:
        raise ValueError("expected_count 必须为正整数")

    _validate_required_columns(labeled_df)

    if len(labeled_df) != expected_count:
        raise ValueError(
            f"标注记录数量不符合预期: 期望 {expected_count}, 实际 {len(labeled_df)}"
        )

    if labeled_df["post_id"].isna().any():
        raise ValueError("post_id 不能为空")

    duplicate_ids = labeled_df["post_id"].duplicated()
    if duplicate_ids.any():
        duplicates = labeled_df.loc[duplicate_ids, "post_id"].tolist()
        raise ValueError(f"存在重复 post_id: {duplicates[:5]}")

    label_invalid = _fetch_invalid_entries(labeled_df["label"], VALID_LABELS)
    if label_invalid:
        raise ValueError(f"label 字段存在非法值: {', '.join(sorted(label_invalid))}")

    strength_invalid = _fetch_invalid_entries(
        labeled_df["strength"], VALID_STRENGTHS
    )
    if strength_invalid:
        raise ValueError(
            f"strength 字段存在非法值: {', '.join(sorted(strength_invalid))}"
        )

