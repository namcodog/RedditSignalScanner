from __future__ import annotations

import json
import re
from typing import Any, Iterable, Mapping

from sqlalchemy import text as sqltext
from sqlalchemy.ext.asyncio import AsyncSession


_TERM_MIN_LEN = 3
_TERM_MAX_LEN = 128
_URL_PATTERN = re.compile(r"https?://|www\.")
_DIGIT_ONLY = re.compile(r"^\d+$")


def _normalize_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.strip().lower())


def _should_keep_term(term: str) -> bool:
    if not term:
        return False
    if len(term) < _TERM_MIN_LEN:
        return False
    if len(term) > _TERM_MAX_LEN:
        return False
    if _DIGIT_ONLY.match(term):
        return False
    if _URL_PATTERN.search(term):
        return False
    return True


def _extract_terms(analysis: Mapping[str, Any]) -> dict[str, set[str]]:
    pains = set(
        _normalize_term(str(t or ""))
        for t in (analysis.get("pain_tags") or [])
        if _should_keep_term(_normalize_term(str(t or "")))
    )
    aspects = set(
        _normalize_term(str(t or ""))
        for t in (analysis.get("aspect_tags") or [])
        if _should_keep_term(_normalize_term(str(t or "")))
    )
    entities = analysis.get("entities") or {}
    known = set(
        _normalize_term(str(t or ""))
        for t in (entities.get("known") or [])
        if _should_keep_term(_normalize_term(str(t or "")))
    )
    new = set(
        _normalize_term(str(t or ""))
        for t in (entities.get("new") or [])
        if _should_keep_term(_normalize_term(str(t or "")))
    )
    brands = known | new
    return {
        "pain_point": pains,
        "feature": aspects,
        "brand": brands,
    }


async def _ensure_concept_id(
    session: AsyncSession, *, code: str, name: str, description: str, domain: str = "general"
) -> int:
    row = await session.execute(
        sqltext(
            """
            INSERT INTO semantic_concepts(code, name, description, domain, is_active, created_at, updated_at)
            VALUES (:code, :name, :description, :domain, true, NOW(), NOW())
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                description = EXCLUDED.description,
                domain = EXCLUDED.domain,
                updated_at = NOW()
            RETURNING id
            """
        ),
        {"code": code, "name": name, "description": description, "domain": domain},
    )
    return int(row.scalar_one())


async def _upsert_semantic_term(
    session: AsyncSession,
    *,
    canonical: str,
    category: str,
    layer: str | None,
    weight: float,
    precision_tag: str,
) -> None:
    await session.execute(
        sqltext(
            """
            INSERT INTO semantic_terms (
                canonical, aliases, category, layer, precision_tag, weight, polarity, lifecycle, created_at, updated_at
            )
            VALUES (:canonical, NULL, :category, :layer, :precision_tag, :weight, NULL, 'approved', NOW(), NOW())
            ON CONFLICT (canonical) DO UPDATE
            SET updated_at = NOW()
            """
        ),
        {
            "canonical": canonical,
            "category": category,
            "layer": layer,
            "precision_tag": precision_tag,
            "weight": weight,
        },
    )


async def _upsert_semantic_rule(
    session: AsyncSession,
    *,
    concept_id: int,
    term: str,
    rule_type: str,
    weight: float,
    meta: dict[str, Any],
) -> None:
    await session.execute(
        sqltext(
            """
            INSERT INTO semantic_rules(concept_id, term, rule_type, weight, is_active, meta, created_at, updated_at)
            VALUES (:concept_id, :term, :rule_type, :weight, true, CAST(:meta AS jsonb), NOW(), NOW())
            ON CONFLICT (concept_id, term, rule_type) DO UPDATE
            SET is_active = true,
                weight = GREATEST(semantic_rules.weight, EXCLUDED.weight),
                meta = CAST(:meta AS jsonb),
                updated_at = NOW()
            """
        ),
        {
            "concept_id": int(concept_id),
            "term": term,
            "rule_type": rule_type,
            "weight": weight,
            "meta": json.dumps(meta or {}),
        },
    )


async def sync_llm_terms(
    session: AsyncSession,
    *,
    analysis: Mapping[str, Any],
    llm_version: str,
    prompt_version: str,
) -> dict[str, int]:
    terms = _extract_terms(analysis)
    counts = {"pain_point": 0, "feature": 0, "brand": 0}

    pain_concept_id = await _ensure_concept_id(
        session,
        code="pain_keywords",
        name="通用痛点词库",
        description="LLM auto pain keywords",
    )
    feature_concept_id = await _ensure_concept_id(
        session,
        code="llm_features",
        name="LLM Features",
        description="LLM auto feature keywords",
    )
    brand_concept_id = await _ensure_concept_id(
        session,
        code="llm_brands",
        name="LLM Brands",
        description="LLM auto brand keywords",
    )

    for term in sorted(terms["pain_point"]):
        await _upsert_semantic_term(
            session,
            canonical=term,
            category="pain_point",
            layer="L3",
            weight=0.8,
            precision_tag="semantic",
        )
        await _upsert_semantic_rule(
            session,
            concept_id=pain_concept_id,
            term=term,
            rule_type="pain_keywords",
            weight=1.0,
            meta={"source": "llm", "llm_version": llm_version, "prompt_version": prompt_version, "category": "pain_point"},
        )
        counts["pain_point"] += 1

    for term in sorted(terms["feature"]):
        await _upsert_semantic_term(
            session,
            canonical=term,
            category="feature",
            layer="L2",
            weight=0.6,
            precision_tag="semantic",
        )
        await _upsert_semantic_rule(
            session,
            concept_id=feature_concept_id,
            term=term,
            rule_type="keyword",
            weight=0.6,
            meta={"source": "llm", "llm_version": llm_version, "prompt_version": prompt_version, "category": "feature"},
        )
        counts["feature"] += 1

    for term in sorted(terms["brand"]):
        await _upsert_semantic_term(
            session,
            canonical=term,
            category="brand",
            layer="L2",
            weight=0.6,
            precision_tag="semantic",
        )
        await _upsert_semantic_rule(
            session,
            concept_id=brand_concept_id,
            term=term,
            rule_type="keyword",
            weight=0.6,
            meta={"source": "llm", "llm_version": llm_version, "prompt_version": prompt_version, "category": "brand"},
        )
        counts["brand"] += 1

    return counts


__all__ = ["sync_llm_terms"]
