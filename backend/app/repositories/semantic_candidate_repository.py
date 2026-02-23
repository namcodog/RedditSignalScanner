from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Tuple

from sqlalchemy import Select, case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semantic_candidate import SemanticCandidate
from app.models.semantic_term import SemanticTerm
from app.repositories.semantic_term_repository import SemanticTermRepository


_CANDIDATE_TERMS_CONCEPT_ID: int | None = None


async def _ensure_candidate_terms_concept_id(session: AsyncSession) -> int:
    global _CANDIDATE_TERMS_CONCEPT_ID
    if _CANDIDATE_TERMS_CONCEPT_ID is not None:
        return _CANDIDATE_TERMS_CONCEPT_ID

    from sqlalchemy import text as sqltext

    exists = (
        await session.execute(sqltext("SELECT to_regclass('public.semantic_concepts')"))
    ).scalar_one_or_none()
    if not exists:
        _CANDIDATE_TERMS_CONCEPT_ID = 0
        return 0

    cid = (
        await session.execute(
            sqltext(
                """
                INSERT INTO semantic_concepts(code, name, description, domain, is_active, created_at, updated_at)
                VALUES ('candidate_terms', 'Candidate Terms', 'Auto-mined candidate terms (pre-approval)', 'general', true, NOW(), NOW())
                ON CONFLICT (code) DO UPDATE
                SET updated_at = NOW()
                RETURNING id
                """
            )
        )
    ).scalar_one()
    _CANDIDATE_TERMS_CONCEPT_ID = int(cid)
    return int(cid)


async def _upsert_candidate_rule(
    session: AsyncSession,
    *,
    term: str,
    source: str,
    frequency: int,
) -> None:
    concept_id = await _ensure_candidate_terms_concept_id(session)
    if concept_id <= 0:
        return
    from sqlalchemy import text as sqltext
    import json

    now = datetime.now(timezone.utc)
    payload = {
        "status": "candidate",
        "source": source,
        "frequency": int(frequency),
        "last_seen_at": now.isoformat(),
    }
    await session.execute(
        sqltext(
            """
            INSERT INTO semantic_rules(concept_id, term, rule_type, weight, is_active, meta, created_at, updated_at)
            VALUES (:concept_id, :term, 'candidate_term', 1.0, false, CAST(:meta AS jsonb), NOW(), NOW())
            ON CONFLICT (concept_id, term, rule_type) DO UPDATE
            SET meta = CAST(:meta AS jsonb),
                updated_at = NOW()
            """
        ),
        {"concept_id": int(concept_id), "term": term.strip().lower(), "meta": json.dumps(payload)},
    )


async def _activate_candidate_rule(
    session: AsyncSession,
    *,
    term: str,
    category: str,
    layer: str,
    aliases: list[str] | None,
    weight: float | None,
) -> None:
    concept_id = await _ensure_candidate_terms_concept_id(session)
    if concept_id <= 0:
        return
    from sqlalchemy import text as sqltext
    import json

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "status": "active",
        "category": category,
        "layer": layer,
        "aliases": aliases or [],
        "approved_at": now.isoformat(),
    }
    await session.execute(
        sqltext(
            """
            INSERT INTO semantic_rules(concept_id, term, rule_type, weight, is_active, meta, created_at, updated_at)
            VALUES (:concept_id, :term, 'candidate_term', :weight, true, CAST(:meta AS jsonb), NOW(), NOW())
            ON CONFLICT (concept_id, term, rule_type) DO UPDATE
            SET is_active = true,
                weight = EXCLUDED.weight,
                meta = CAST(:meta AS jsonb),
                updated_at = NOW()
            """
        ),
        {
            "concept_id": int(concept_id),
            "term": term.strip().lower(),
            "weight": float(weight) if weight is not None else 1.0,
            "meta": json.dumps(payload),
        },
    )


class SemanticCandidateRepository:
    """Repository for semantic_candidates workflow and aggregation operations."""

    def __init__(
        self, session: AsyncSession, term_repository: SemanticTermRepository
    ) -> None:
        self._session = session
        self._term_repository = term_repository

    async def get_pending(self, limit: int = 100) -> List[SemanticCandidate]:
        stmt: Select[tuple[SemanticCandidate]] = (
            select(SemanticCandidate)
            .where(SemanticCandidate.status == "pending")
            .order_by(SemanticCandidate.frequency.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(self, term: str, source: str) -> SemanticCandidate:
        now = datetime.now(timezone.utc)
        stmt = (
            insert(SemanticCandidate)
            .values(
                term=term,
                source=source,
                frequency=1,
                first_seen_at=now,
                last_seen_at=now,
                status="pending",
            )
            .on_conflict_do_update(
                index_elements=[SemanticCandidate.term],
                set_={
                    "frequency": SemanticCandidate.frequency + 1,
                    "last_seen_at": now,
                },
            )
            .returning(SemanticCandidate)
        )
        result = await self._session.execute(stmt)
        candidate = result.scalars().one()
        # ensure in-memory state reflects updated frequency / last_seen_at
        await self._session.refresh(candidate)
        await _upsert_candidate_rule(
            self._session, term=candidate.term, source=source, frequency=int(candidate.frequency or 1)
        )
        return candidate

    async def bulk_upsert(
        self,
        items: Iterable[Tuple[str, int]],
        source: str,
    ) -> List[SemanticCandidate]:
        """Batch upsert candidates using a single ON CONFLICT statement."""
        now = datetime.now(timezone.utc)
        rows: list[dict[str, Any]] = []
        for term, frequency in items:
            rows.append(
                {
                    "term": term,
                    "source": source,
                    "frequency": int(frequency),
                    "first_seen_at": now,
                    "last_seen_at": now,
                    "status": "pending",
                }
            )

        if not rows:
            return []

        batch_size = 500
        candidates: list[SemanticCandidate] = []
        for start in range(0, len(rows), batch_size):
            chunk = rows[start : start + batch_size]
            stmt = insert(SemanticCandidate).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=[SemanticCandidate.term],
                set_={
                    "frequency": SemanticCandidate.frequency + stmt.excluded.frequency,
                    "last_seen_at": now,
                },
            ).returning(SemanticCandidate)
            result = await self._session.execute(stmt)
            chunk_candidates = list(result.scalars().all())
            candidates.extend(chunk_candidates)
            for c in chunk_candidates:
                try:
                    await _upsert_candidate_rule(
                        self._session,
                        term=str(c.term),
                        source=source,
                        frequency=int(c.frequency or 1),
                    )
                except Exception:
                    continue
        return candidates

    async def approve(
        self,
        candidate_id: int,
        category: str,
        layer: str,
        operator_id,
    ) -> SemanticTerm:
        async with self._session.begin_nested():
            stmt: Select[tuple[SemanticCandidate]] = select(SemanticCandidate).where(
                SemanticCandidate.id == candidate_id
            )
            result = await self._session.execute(stmt)
            candidate = result.scalars().first()
            if candidate is None:
                raise ValueError(f"SemanticCandidate {candidate_id} not found")

            term = SemanticTerm(
                canonical=candidate.term,
                aliases=None,
                category=category,
                layer=layer,
                precision_tag="exact",
                weight=1.0,
                polarity=None,
            )
            await self._term_repository.create(term)
            await self._session.delete(candidate)

        # Step 9: Promote candidate -> active in semantic_rules (single source for runtime)
        try:
            await _activate_candidate_rule(
                self._session,
                term=term.canonical,
                category=category,
                layer=layer,
                aliases=term.aliases or None,
                weight=float(term.weight) if term.weight is not None else None,
            )
        except Exception:
            # best-effort; do not fail approval
            pass
        
        # Phase 1.4: Publish event
        from app.events.semantic_bus import Events, get_event_bus
        await get_event_bus().publish(
            Events.CANDIDATE_APPROVED,
            {"term_id": term.id, "canonical": term.canonical}
        )
        return term

    async def reject(
        self, candidate_id: int, reason: str, operator_id
    ) -> None:
        stmt: Select[tuple[SemanticCandidate]] = select(SemanticCandidate).where(
            SemanticCandidate.id == candidate_id
        )
        result = await self._session.execute(stmt)
        candidate = result.scalars().first()
        if candidate is None:
            return
        candidate.status = "rejected"
        candidate.reject_reason = reason
        candidate.reviewed_by = operator_id
        candidate.reviewed_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def get_statistics(self) -> Dict[str, Any]:
        stmt = select(
            func.count().label("total"),
            func.sum(
                case(
                    (SemanticCandidate.status == "pending", 1),
                    else_=0,
                )
            ).label("pending"),
            func.sum(
                case(
                    (SemanticCandidate.status == "approved", 1),
                    else_=0,
                )
            ).label("approved"),
            func.sum(
                case(
                    (SemanticCandidate.status == "rejected", 1),
                    else_=0,
                )
            ).label("rejected"),
        )
        result = await self._session.execute(stmt)
        row = result.one()

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        this_week_stmt = select(
            func.count().label("this_week_new")
        ).where(SemanticCandidate.first_seen_at >= week_ago)
        this_week_result = await self._session.execute(this_week_stmt)
        this_week_new = this_week_result.scalar() or 0

        return {
            "total": int(row.total or 0),
            "pending": int(row.pending or 0),
            "approved": int(row.approved or 0),
            "rejected": int(row.rejected or 0),
            "this_week_new": int(this_week_new),
        }

    async def update(self, term_id: int, updates: dict[str, Any]) -> SemanticTerm:
        """Forward updates to semantic_terms via the term repository."""
        return await self._term_repository.update(term_id, updates)


__all__ = ["SemanticCandidateRepository"]
