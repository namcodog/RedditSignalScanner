from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Mapping, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.brand_intelligence.brand_system_evidence import (
    load_brand_system_evidence,
)
from app.services.community.community_recommendation_models import CommunitySignal
from app.services.hotpost.hotpost_community_activity import normalize_community_key


@dataclass(frozen=True)
class CommunityBrandEvidence:
    community: str
    brand_terms: tuple[str, ...]
    brand_mentions: int
    brand_count: int

    @property
    def key(self) -> str:
        return cast(str, normalize_community_key(self.community))


async def load_community_brand_evidence(
    session: AsyncSession,
    *,
    limit: int = 120,
) -> tuple[CommunityBrandEvidence, ...]:
    payload = await load_brand_system_evidence(session, limit=max(1, limit))
    return community_brand_evidence_from_payload(payload)


def community_brand_evidence_from_payload(
    payload: Mapping[str, object],
) -> tuple[CommunityBrandEvidence, ...]:
    rows = payload.get("community_brand_evidence")
    if not isinstance(rows, list):
        return ()
    return tuple(
        _evidence_from_row(_mapping(row)) for row in rows if isinstance(row, dict)
    )


def merge_community_brand_evidence(
    signals: Iterable[CommunitySignal],
    evidence: Iterable[CommunityBrandEvidence],
) -> tuple[CommunitySignal, ...]:
    by_key = {item.key: item for item in evidence if item.key}
    merged: list[CommunitySignal] = []
    for signal in signals:
        item = by_key.get(signal.key)
        if item is None:
            merged.append(signal)
            continue
        merged.append(
            replace(
                signal,
                brand_terms=item.brand_terms,
                brand_mentions=item.brand_mentions,
                brand_count=item.brand_count,
            )
        )
    return tuple(merged)


def _evidence_from_row(row: Mapping[str, object]) -> CommunityBrandEvidence:
    brands = row.get("brands")
    names = (
        tuple(
            _text(_mapping(item).get("display_name"))
            for item in brands
            if isinstance(item, dict)
        )
        if isinstance(brands, list)
        else ()
    )
    return CommunityBrandEvidence(
        community=_text(row.get("community")),
        brand_terms=tuple(item for item in names if item)[:5],
        brand_mentions=_int(row.get("mention_count")),
        brand_count=_int(row.get("brand_count")),
    )


def _mapping(value: object) -> dict[str, object]:
    return dict(cast(Mapping[str, object], value)) if isinstance(value, dict) else {}


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _int(value: object) -> int:
    return int(value) if isinstance(value, int | str) and str(value).isdigit() else 0
