from __future__ import annotations

from typing import List

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semantic_term import SemanticTerm


class SemanticTermRepository:
    """Repository for semantic_terms table CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self, lifecycle: str = "approved") -> List[SemanticTerm]:
        stmt: Select[tuple[SemanticTerm]] = select(SemanticTerm).where(
            SemanticTerm.lifecycle == lifecycle
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category(
        self, category: str, layer: str | None = None
    ) -> List[SemanticTerm]:
        stmt: Select[tuple[SemanticTerm]] = select(SemanticTerm).where(
            SemanticTerm.category == category
        )
        if layer is not None:
            stmt = stmt.where(SemanticTerm.layer == layer)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, term: SemanticTerm) -> SemanticTerm:
        self._session.add(term)
        await self._session.flush()
        await self._session.refresh(term)
        return term

    async def update(self, term_id: int, updates: dict) -> SemanticTerm:
        stmt: Select[tuple[SemanticTerm]] = select(SemanticTerm).where(
            SemanticTerm.id == term_id
        )
        result = await self._session.execute(stmt)
        term = result.scalars().first()
        if term is None:
            raise ValueError(f"SemanticTerm {term_id} not found")

        for key, value in updates.items():
            if hasattr(term, key):
                setattr(term, key, value)

        await self._session.flush()
        await self._session.refresh(term)
        return term

    async def delete(self, term_id: int) -> None:
        stmt: Select[tuple[SemanticTerm]] = select(SemanticTerm).where(
            SemanticTerm.id == term_id
        )
        result = await self._session.execute(stmt)
        term = result.scalars().first()
        if term is None:
            return
        await self._session.delete(term)

    async def search(self, query: str) -> List[SemanticTerm]:
        pattern = f"%{query}%"
        stmt: Select[tuple[SemanticTerm]] = select(SemanticTerm).where(
            SemanticTerm.canonical.ilike(pattern)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


__all__ = ["SemanticTermRepository"]
