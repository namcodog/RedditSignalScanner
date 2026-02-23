from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.semantic_candidate import SemanticCandidate
from app.repositories.semantic_candidate_repository import SemanticCandidateRepository
from app.repositories.semantic_term_repository import SemanticTermRepository
from app.services.semantic.candidate_extractor import CandidateExtractor
from app.services.semantic.llm_candidate_extractor import (
    LlmCandidateStats,
    extract_llm_candidates,
)
from app.services.semantic.smart_tagger import SemanticTagger
from app.services.semantic.unified_lexicon import UnifiedLexicon

logger = logging.getLogger(__name__)
task_logger = get_task_logger(__name__)


async def _run_extract_semantic_candidates(lookback_days: int = 90) -> Dict[str, Any]:
    async with SessionFactory() as session:
        # 构建语义库（YAML 为兜底，真实环境中语义表会逐步接管）
        lex_path_env = Path(
            Path(
                __file__,
            )
            .resolve()
            .parents[3]
            / "backend"
            / "config"
            / "semantic_sets"
            / "unified_lexicon.yml"
        )
        lexicon = UnifiedLexicon(lex_path_env)
        extractor = CandidateExtractor(lexicon=lexicon, min_frequency=5)

        term_repo = SemanticTermRepository(session)
        cand_repo = SemanticCandidateRepository(session, term_repo)

        candidates = await extractor.extract_from_db(
            session=session,
            repository=cand_repo,
            lookback_days=lookback_days,
        )
        await session.commit()

        total = len(candidates)
        top_terms: List[str] = [
            c.term for c in sorted(candidates, key=lambda c: (-c.frequency, c.term))[:20]
        ]
        return {
            "total_candidates": total,
            "top_terms": top_terms,
        }


@celery_app.task(  # type: ignore[misc]
    name="tasks.semantic.extract_candidates",
    time_limit=60 * 30,  # 30 minutes
)
def extract_semantic_candidates_weekly() -> Dict[str, Any]:
    """Celery entrypoint for weekly semantic candidate extraction."""
    try:
        result = asyncio.run(_run_extract_semantic_candidates(lookback_days=90))
        task_logger.info(
            "Semantic candidates extraction completed",
            extra={
                "total_candidates": result.get("total_candidates", 0),
                "top_terms": result.get("top_terms", []),
            },
        )
        return result
    except Exception:
        task_logger.exception("Semantic candidates extraction failed")
        # 任务仍然返回结构化信息，便于上层监控
        return {
            "total_candidates": 0,
            "top_terms": [],
            "error": "extraction_failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def _pick_category(categories: set[str]) -> tuple[str, str]:
    if "pain_point" in categories:
        return "pain_point", "L3"
    if "feature" in categories:
        return "feature", "L3"
    if "brand" in categories:
        return "brand", "entity"
    return "feature", "L3"


def _should_auto_approve(
    stat: LlmCandidateStats,
    *,
    total_frequency: int,
    min_confidence: float,
    min_frequency: int,
    min_communities: int,
    min_authors: int,
) -> bool:
    if stat.max_confidence < min_confidence:
        return False
    if total_frequency < min_frequency:
        return False
    if len(stat.subreddits) >= min_communities:
        return True
    if len(stat.authors) >= min_authors:
        return True
    return False


async def _run_llm_candidate_sync() -> Dict[str, Any]:
    settings = get_settings()
    lookback_days = int(settings.llm_semantic_lookback_days)
    post_limit = int(settings.llm_semantic_post_limit)
    comment_limit = int(settings.llm_semantic_comment_limit)
    min_conf = float(settings.llm_semantic_min_confidence)
    min_freq = int(settings.llm_semantic_min_frequency)
    min_communities = int(settings.llm_semantic_min_communities)
    min_authors = int(settings.llm_semantic_min_authors)
    auto_approve = bool(settings.llm_semantic_auto_approve)

    async with SessionFactory() as session:
        term_repo = SemanticTermRepository(session)
        existing_terms = [t.canonical for t in await term_repo.get_all()]
        stats = await extract_llm_candidates(
            session=session,
            lookback_days=lookback_days,
            post_limit=post_limit,
            comment_limit=comment_limit,
            existing_terms=existing_terms,
        )

        if not stats:
            return {
                "candidates": 0,
                "auto_approved": 0,
                "pending": 0,
            }

        cand_repo = SemanticCandidateRepository(session, term_repo)

        pending_rows = await session.execute(
            select(SemanticCandidate.term, SemanticCandidate.frequency).where(
                SemanticCandidate.status == "pending"
            )
        )
        existing_candidate_freq = {
            str(row[0]).strip().lower(): int(row[1] or 0)
            for row in pending_rows.all()
            if row[0]
        }

        items = [(term, stat.frequency) for term, stat in stats.items()]
        candidates = await cand_repo.bulk_upsert(items, source="llm")
        candidate_map = {str(c.term).strip().lower(): c for c in candidates}

        auto_approved = 0
        pending = 0
        for term, stat in stats.items():
            total_freq = stat.frequency + existing_candidate_freq.get(term, 0)
            if auto_approve and _should_auto_approve(
                stat,
                total_frequency=total_freq,
                min_confidence=min_conf,
                min_frequency=min_freq,
                min_communities=min_communities,
                min_authors=min_authors,
            ):
                candidate = candidate_map.get(term)
                if candidate is None:
                    pending += 1
                    continue
                category, layer = _pick_category(stat.categories)
                await cand_repo.approve(
                    candidate.id,
                    category=category,
                    layer=layer,
                    operator_id=None,
                )
                auto_approved += 1
            else:
                pending += 1

        await session.commit()
        return {
            "candidates": len(items),
            "auto_approved": auto_approved,
            "pending": pending,
        }


@celery_app.task(  # type: ignore[misc]
    name="tasks.semantic.sync_llm_candidates",
    time_limit=60 * 20,
)
def sync_llm_candidates() -> Dict[str, Any]:
    """从 LLM 标签抽候选词，自动回流语义库。"""
    try:
        result = asyncio.run(_run_llm_candidate_sync())
        task_logger.info("LLM candidates sync completed", extra=result)
        return result
    except Exception:
        task_logger.exception("LLM candidates sync failed")
        return {
            "candidates": 0,
            "auto_approved": 0,
            "pending": 0,
            "error": "sync_failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


__all__ = [
    "extract_semantic_candidates_weekly",
    "sync_llm_candidates",
    "tag_post_semantics",
    "tag_posts_batch",
]


@celery_app.task(  # type: ignore[misc]
    name="tasks.semantic.tag_post_semantics",
    time_limit=60 * 5,
)
def tag_post_semantics(post_id: int) -> Dict[str, Any]:
    """实时语义打标（单帖）。"""
    tagger = SemanticTagger()
    try:
        result = tagger.process_single(post_id)
        task_logger.info("post tagged", extra={"post_id": post_id, "status": result.get("status")})
        return result
    except Exception:
        task_logger.exception("post tagging failed", extra={"post_id": post_id})
        return {"post_id": post_id, "status": "error"}


@celery_app.task(  # type: ignore[misc]
    name="tasks.semantic.tag_posts_batch",
    time_limit=60 * 15,
)
def tag_posts_batch(limit: int = 500) -> Dict[str, Any]:
    """定时兜底批量打标（只写 post_semantic_labels，安全幂等）。"""
    tagger = SemanticTagger()
    try:
        result = tagger.process_batch(limit=limit)
        task_logger.info("batch tagging completed", extra=result)
        return result
    except Exception:
        task_logger.exception("batch tagging failed")
        return {"processed": 0, "status": "error"}
