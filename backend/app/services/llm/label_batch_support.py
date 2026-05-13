from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.services.llm.interfaces import LLMClientError

logger = logging.getLogger(__name__)

SingleLabelResult = tuple[dict[str, Any], Any, int, int]
BatchLabelFn = Callable[[Sequence[dict[str, Any]]], Awaitable[list[dict[str, Any]]]]
SingleLabelFn = Callable[[dict[str, Any]], Awaitable[SingleLabelResult]]
PersistBatchFn = Callable[[dict[str, Any]], Awaitable[None]]
PersistSingleFn = Callable[[dict[str, Any], SingleLabelResult], Awaitable[None]]


def chunk_items(items: Sequence[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


def json_sanitize(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: json_sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_sanitize(v) for v in value]
    return value


def should_use_long_lab(
    *,
    row_id: int,
    value_score: float,
    mid_score_min: float,
    mid_score_max: float,
    sample_rate: float,
) -> bool:
    if mid_score_min <= value_score <= mid_score_max:
        return True
    bucket = abs(int(row_id)) % 100
    return bucket < int(sample_rate * 100)


def split_limits(limit: int, high_ratio: float) -> tuple[int, int]:
    if limit <= 0:
        return 0, 0
    high_limit = int(round(limit * high_ratio))
    high_limit = min(limit, max(0, high_limit))
    mid_limit = max(0, limit - high_limit)
    return mid_limit, high_limit


def build_post_item(
    row: dict[str, Any],
    *,
    top_comments: list[str],
) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "title": row.get("title") or "",
        "body": row.get("body") or "",
        "subreddit": row.get("subreddit") or "",
        "comments": top_comments,
    }


def build_comment_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "body": row.get("body") or "",
        "post_title": row.get("post_title") or "",
        "subreddit": row.get("subreddit") or "",
    }


@dataclass
class LLMLabelRunStats:
    attempted: int = 0
    processed: int = 0
    fallback_batches: int = 0
    llm_failures: int = 0
    persist_failures: int = 0
    degraded_reasons: list[str] = field(default_factory=list)

    def mark_degraded(self, reason: str) -> None:
        if reason not in self.degraded_reasons:
            self.degraded_reasons.append(reason)

    def to_result(self) -> dict[str, Any]:
        if self.processed == 0 and (self.llm_failures > 0 or self.persist_failures > 0):
            status = "failed"
        elif self.degraded_reasons:
            status = "degraded"
        else:
            status = "completed"
        return {
            "processed": self.processed,
            "attempted": self.attempted,
            "status": status,
            "fallback_batches": self.fallback_batches,
            "llm_failures": self.llm_failures,
            "persist_failures": self.persist_failures,
            "degraded_reasons": self.degraded_reasons,
        }


async def process_label_batches(
    *,
    session: Any,
    items: Sequence[dict[str, Any]],
    batch_size: int,
    label_kind: str,
    stats: LLMLabelRunStats,
    batch_label: BatchLabelFn,
    single_label: SingleLabelFn,
    persist_batch: PersistBatchFn,
    persist_single: PersistSingleFn,
) -> None:
    for batch in chunk_items(items, batch_size):
        batch_processed = 0
        request_failed = False
        try:
            results = await batch_label(batch)
        except LLMClientError as exc:
            request_failed = True
            results = []
            stats.llm_failures += len(batch)
            stats.mark_degraded("batch_llm_request_failed")
            logger.warning("%s batch request failed size=%s", label_kind, len(batch), exc_info=exc)
        except Exception as exc:
            request_failed = True
            results = []
            stats.llm_failures += len(batch)
            stats.mark_degraded("batch_label_unexpected_error")
            logger.warning("%s batch call failed size=%s", label_kind, len(batch), exc_info=exc)

        if not results:
            stats.fallback_batches += 1
            if not request_failed:
                stats.mark_degraded("batch_empty_fallback")
            for item in batch:
                try:
                    single_result = await single_label(item)
                except LLMClientError as exc:
                    stats.llm_failures += 1
                    stats.mark_degraded("single_llm_request_failed")
                    logger.warning(
                        "%s single fallback request failed item_id=%s",
                        label_kind,
                        item.get("id"),
                        exc_info=exc,
                    )
                    continue
                except Exception as exc:
                    stats.llm_failures += 1
                    stats.mark_degraded("single_label_unexpected_error")
                    logger.warning(
                        "%s single fallback call failed item_id=%s",
                        label_kind,
                        item.get("id"),
                        exc_info=exc,
                    )
                    continue

                try:
                    async with session.begin_nested():
                        await persist_single(item, single_result)
                    batch_processed += 1
                except Exception as exc:
                    stats.persist_failures += 1
                    stats.mark_degraded("persist_failed")
                    logger.warning(
                        "%s single fallback persist failed item_id=%s",
                        label_kind,
                        item.get("id"),
                        exc_info=exc,
                    )

            await _commit_batch(session=session, stats=stats, label_kind=label_kind, batch_processed=batch_processed)
            continue

        for result in results:
            try:
                async with session.begin_nested():
                    await persist_batch(result)
                batch_processed += 1
            except Exception as exc:
                stats.persist_failures += 1
                stats.mark_degraded("persist_failed")
                logger.warning(
                    "%s batch persist failed item_id=%s",
                    label_kind,
                    result.get("id"),
                    exc_info=exc,
                )

        await _commit_batch(session=session, stats=stats, label_kind=label_kind, batch_processed=batch_processed)


async def _commit_batch(
    *,
    session: Any,
    stats: LLMLabelRunStats,
    label_kind: str,
    batch_processed: int,
) -> None:
    try:
        await session.commit()
        stats.processed += batch_processed
    except Exception as exc:
        await session.rollback()
        if batch_processed > 0:
            stats.persist_failures += batch_processed
            stats.mark_degraded("commit_failed")
        logger.warning("%s batch commit failed size=%s", label_kind, batch_processed, exc_info=exc)
