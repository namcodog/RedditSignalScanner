"""
Core application utilities and shared configuration.

This package currently bootstraps the Celery app required by
PRD/PRD-04-任务系统.md, exposing `app.core.celery_app`.
"""

from __future__ import annotations

__all__ = ["celery_app"]
