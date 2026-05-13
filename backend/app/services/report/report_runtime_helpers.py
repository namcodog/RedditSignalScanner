from __future__ import annotations

import logging
from html import escape as _escape
from typing import Any, Awaitable, Callable

from app.core.config import settings
from app.schemas.analysis import AnalysisRead, CommunitySourceDetail
from app.schemas.report_payload import ReportOverview, ReportStats
from app.services.report.analysis_payload_loader import (
    AnalysisPayloadValidationError,
    format_analysis_version,
    validate_report_analysis_payload,
)
from app.services.report.community_member_count_provider import (
    resolve_community_member_count,
)
from app.services.report.report_payload_builder import build_report_overview

logger = logging.getLogger(__name__)


def resolve_report_quality_level() -> str:
    try:
        return str(getattr(settings, "report_quality_level", "standard")).strip().lower()
    except Exception:
        return "standard"


def is_market_mode_enabled() -> bool:
    try:
        report_mode = str(getattr(settings, "report_mode", "technical")).strip().lower()
        return bool(
            getattr(settings, "enable_market_report", False)
            or report_mode == "market"
        )
    except Exception:
        return False


def validate_runtime_analysis_payload(
    analysis: Any,
    *,
    target_analysis_version: Any,
    error_cls: type[Exception],
) -> AnalysisRead:
    try:
        return validate_report_analysis_payload(
            analysis=analysis,
            target_analysis_version=target_analysis_version,
        )
    except AnalysisPayloadValidationError as exc:
        logger.exception(
            "Analysis payload validation failed for analysis=%s",
            getattr(analysis, "id", "unknown"),
        )
        raise error_cls("Failed to validate analysis payload") from exc


async def fetch_runtime_community_member_count(
    community_name: str,
    *,
    repository: Any,
    configured_member_counts: dict[str, int],
) -> int:
    fetch_db_member_count = getattr(
        repository,
        "get_community_member_count",
        None,
    )

    async def _fallback_fetch(_: str) -> int | None:
        return None

    return await resolve_community_member_count(
        community_name,
        fetch_db_member_count=(
            fetch_db_member_count
            if callable(fetch_db_member_count)
            else _fallback_fetch
        ),
        configured_member_counts=configured_member_counts,
    )


async def build_runtime_overview(
    communities_detail: list[CommunitySourceDetail],
    stats: ReportStats,
    *,
    fetch_member_count: Callable[[str], Awaitable[int]],
) -> ReportOverview:
    return await build_report_overview(
        communities_detail,
        stats,
        fetch_member_count=fetch_member_count,
    )


def coerce_runtime_report_html(raw: str | None) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if "<html" in lowered or "<body" in lowered or "<p" in lowered or "<h" in lowered:
        return text
    try:
        import markdown as _md  # type: ignore

        return _md.markdown(text, extensions=["extra", "tables"])
    except Exception:
        return f"<pre>{_escape(text)}</pre>"


def format_runtime_analysis_version(version: Any) -> str:
    if version is None:
        return "unknown"
    return format_analysis_version(version)


__all__ = [
    "build_runtime_overview",
    "coerce_runtime_report_html",
    "fetch_runtime_community_member_count",
    "format_runtime_analysis_version",
    "is_market_mode_enabled",
    "resolve_report_quality_level",
    "validate_runtime_analysis_payload",
]
