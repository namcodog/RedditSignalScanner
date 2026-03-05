from __future__ import annotations

"""Compatibility shim for legacy imports.

This module re-exports the labeling helpers from app.services.labeling package
to preserve legacy import paths after Phase E service reorganization.
"""

from app.services.labeling import (
    SAMPLE_COLUMNS,
    classify_and_label_comments,
    export_samples_to_csv,
    extract_and_label_entities_for_comments,
    load_labeled_data,
    sample_posts_for_labeling,
    validate_labels,
    _extract_entities_from_text,
)

__all__ = [
    "SAMPLE_COLUMNS",
    "classify_and_label_comments",
    "export_samples_to_csv",
    "extract_and_label_entities_for_comments",
    "load_labeled_data",
    "sample_posts_for_labeling",
    "validate_labels",
    "_extract_entities_from_text",
]
