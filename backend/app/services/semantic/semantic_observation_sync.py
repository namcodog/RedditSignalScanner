from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import ContentEntity, ContentLabel
from app.models.llm_labels import CommentLLMLabel, PostLLMLabel
from app.models.post_semantic_label import PostSemanticLabel
from app.models.semantic_observation import SemanticObservation
from app.models.semantic_term import SemanticTerm


def _normalize_text(value: Any) ->Optional[ str]:
    text = str(value or "").strip()
    return text or None


def _to_float(value: Any) ->Optional[ float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_confidence(value: Any) ->Optional[ float]:
    numeric = _to_float(value)
    if numeric is None:
        return None
    if numeric > 1.0:
        numeric = numeric / 100.0
    return max(0.0, min(numeric, 0.9999))


def _iter_llm_tags(tags_analysis:Optional[ dict[str, Any]]) -> Iterable[tuple[str, str]]:
    for key, value in (tags_analysis or {}).items():
        if isinstance(value, list):
            for item in value:
                text = _normalize_text(item)
                if text:
                    yield key, text
            continue
        text = _normalize_text(value)
        if text:
            yield key, text


def _iter_llm_entities(raw: Any) -> Iterable[str]:
    if isinstance(raw, list):
        for item in raw:
            text = _normalize_text(item)
            if text:
                yield text
        return
    if isinstance(raw, dict):
        for key, value in raw.items():
            key_text = _normalize_text(key)
            value_text = _normalize_text(value)
            if key_text:
                yield key_text
            if value_text:
                yield value_text


@dataclass(slots=True)
class SemanticSyncResult:
    content_type: str
    content_id: int
    observations_written: int


async def _load_term_ids(
    session: AsyncSession,
    *,
    candidates: set[str],
) -> dict[str, int]:
    if not candidates:
        return {}
    rows = (
        await session.execute(
            select(SemanticTerm).where(SemanticTerm.canonical.in_(sorted(candidates)))
        )
    ).scalars()
    return {str(row.canonical): int(row.id) for row in rows}


def _append_observation(
    rows: list[SemanticObservation],
    *,
    content_type: str,
    content_id: int,
    observation_type: str,
    label_key:Optional[ str],
    label_value:Optional[ str],
    confidence:Optional[ float],
    provenance: str,
    observed_at: datetime,
    source_model:Optional[ str],
    evidence: dict[str, Any],
    term_ids: dict[str, int],
) -> None:
    normalized_value = _normalize_text(label_value)
    if normalized_value is None and label_key is None:
        return
    rows.append(
        SemanticObservation(
            content_type=content_type,
            content_id=content_id,
            observation_type=observation_type,
            term_id=term_ids.get(normalized_value or ""),
            concept_id=None,
            label_key=_normalize_text(label_key),
            label_value=normalized_value,
            confidence=confidence,
            provenance=provenance,
            run_key=f"{content_type}:{content_id}:reconciled",
            source_model=source_model,
            evidence=evidence,
            observed_at=observed_at,
        )
    )


async def sync_semantic_observations(
    session: AsyncSession,
    *,
    content_type: str,
    content_id: int,
    post_semantic_label:Optional[ PostSemanticLabel] = None,
    post_llm_label:Optional[ PostLLMLabel] = None,
    comment_llm_label:Optional[ CommentLLMLabel] = None,
    content_labels: Iterable[ContentLabel] = (),
    content_entities: Iterable[ContentEntity] = (),
) -> SemanticSyncResult:
    observed_at = datetime.now(timezone.utc)
    candidates: set[str] = set()
    if post_semantic_label is not None:
        for value in post_semantic_label.top_terms or []:
            text = _normalize_text(value)
            if text:
                candidates.add(text)
    for entity in content_entities:
        text = _normalize_text(entity.entity)
        if text:
            candidates.add(text)
    llm_label = post_llm_label if content_type == "post" else comment_llm_label
    if llm_label is not None:
        for value in _iter_llm_entities(llm_label.entities_extracted):
            candidates.add(value)
    term_ids = await _load_term_ids(session, candidates=candidates)

    await session.execute(
        delete(SemanticObservation).where(
            SemanticObservation.content_type == content_type,
            SemanticObservation.content_id == content_id,
            SemanticObservation.provenance == "reconciled",
        )
    )

    rows: list[SemanticObservation] = []
    if post_semantic_label is not None:
        for key, value in (
            ("l1_category", post_semantic_label.l1_category),
            ("l2_business", post_semantic_label.l2_business),
            ("l3_scene", post_semantic_label.l3_scene),
        ):
            _append_observation(
                rows,
                content_type=content_type,
                content_id=content_id,
                observation_type="semantic_classification",
                label_key=key,
                label_value=value,
                confidence=_normalize_confidence(post_semantic_label.confidence),
                provenance="reconciled",
                observed_at=observed_at,
                source_model=f"rules:{post_semantic_label.rule_version}",
                evidence={"source": "post_semantic_labels"},
                term_ids=term_ids,
            )
        for term in post_semantic_label.top_terms or []:
            _append_observation(
                rows,
                content_type=content_type,
                content_id=content_id,
                observation_type="semantic_term",
                label_key="top_term",
                label_value=term,
                confidence=_normalize_confidence(post_semantic_label.confidence),
                provenance="reconciled",
                observed_at=observed_at,
                source_model=f"rules:{post_semantic_label.rule_version}",
                evidence={"source": "post_semantic_labels"},
                term_ids=term_ids,
            )

    if llm_label is not None:
        for key, value in _iter_llm_tags(llm_label.tags_analysis):
            _append_observation(
                rows,
                content_type=content_type,
                content_id=content_id,
                observation_type="llm_tag",
                label_key=key,
                label_value=value,
                confidence=None,
                provenance="reconciled",
                observed_at=observed_at,
                source_model=llm_label.model_name or llm_label.llm_version,
                evidence={"source": "llm_labels"},
                term_ids=term_ids,
            )
        for entity in _iter_llm_entities(llm_label.entities_extracted):
            _append_observation(
                rows,
                content_type=content_type,
                content_id=content_id,
                observation_type="llm_entity",
                label_key="entity",
                label_value=entity,
                confidence=None,
                provenance="reconciled",
                observed_at=observed_at,
                source_model=llm_label.model_name or llm_label.llm_version,
                evidence={"source": "llm_labels"},
                term_ids=term_ids,
            )

    for label in content_labels:
        _append_observation(
            rows,
            content_type=content_type,
            content_id=content_id,
            observation_type="content_label",
            label_key=label.category,
            label_value=label.aspect,
            confidence=_normalize_confidence(label.confidence),
            provenance="reconciled",
            observed_at=observed_at,
            source_model="content_labels",
            evidence={"source": "content_labels"},
            term_ids=term_ids,
        )
    for entity in content_entities:
        _append_observation(
            rows,
            content_type=content_type,
            content_id=content_id,
            observation_type="content_entity",
            label_key=entity.entity_type,
            label_value=entity.entity,
            confidence=_to_float(entity.count),
            provenance="reconciled",
            observed_at=observed_at,
            source_model="content_entities",
            evidence={"source": "content_entities"},
            term_ids=term_ids,
        )

    session.add_all(rows)
    await session.flush()
    return SemanticSyncResult(
        content_type=content_type,
        content_id=content_id,
        observations_written=len(rows),
    )


__all__ = ["SemanticSyncResult", "sync_semantic_observations"]
