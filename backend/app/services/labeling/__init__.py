"""
Labeling utilities package.

Phase 3 adds sampling, exporting and validation helpers to support the
human-in-the-loop annotation workflow described in the execution plan.
"""

from .sampler import (
    SAMPLE_COLUMNS,
    export_samples_to_csv,
    load_labeled_data,
    sample_posts_for_labeling,
)
from .validator import validate_labels
from .comments_labeling import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
    _extract_entities_from_text,
)

__all__ = [
    "SAMPLE_COLUMNS",
    "export_samples_to_csv",
    "load_labeled_data",
    "sample_posts_for_labeling",
    "validate_labels",
    "classify_and_label_comments",
    "extract_and_label_entities_for_comments",
    "_extract_entities_from_text",
]
