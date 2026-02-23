from __future__ import annotations

"""Compatibility shim for legacy imports.

This module re-exports the labeling functions from the package implementation
under app.services.labeling.comments_labeling to avoid duplicate logic and
eliminate ambiguity between module and package imports.
"""

from app.services.labeling.comments_labeling import (
    classify_and_label_comments,
    extract_and_label_entities_for_comments,
    _extract_entities_from_text,
)

__all__ = [
    "classify_and_label_comments",
    "extract_and_label_entities_for_comments",
    "_extract_entities_from_text",
]
