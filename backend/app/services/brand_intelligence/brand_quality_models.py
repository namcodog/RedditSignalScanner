from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EvidenceThreshold:
    min_mentions: int
    min_communities: int


@dataclass(frozen=True)
class BrandQualityRules:
    verified_thresholds: Mapping[str, EvidenceThreshold]
    generic_terms: frozenset[str]
    person_name_surnames: frozenset[str]


@dataclass(frozen=True)
class InterestTagRule:
    display_name: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class BrandQualityItem:
    canonical_name: str
    review_status: str
    source_lifecycle: str
    mention_count: int
    community_count: int
    interest_tags: tuple[str, ...]
    noise_flags: tuple[str, ...]
    reason: str

    def to_payload(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "review_status": self.review_status,
            "source_lifecycle": self.source_lifecycle,
            "mention_count": self.mention_count,
            "community_count": self.community_count,
            "interest_tags": list(self.interest_tags),
            "noise_flags": list(self.noise_flags),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class BrandQualityReport:
    report_date: str
    card_count: int
    items: tuple[BrandQualityItem, ...]

    @property
    def noise_items(self) -> tuple[BrandQualityItem, ...]:
        return tuple(item for item in self.items if item.noise_flags)

    @property
    def summary(self) -> dict[str, object]:
        status_counts: dict[str, int] = {}
        tag_counts: dict[str, int] = {}
        for item in self.items:
            status_counts[item.review_status] = (
                status_counts.get(item.review_status, 0) + 1
            )
            for tag in item.interest_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return {
            "report_date": self.report_date,
            "source": "brand_digest",
            "db_writes": False,
            "card_count": self.card_count,
            "brand_count": len(self.items),
            "noise_count": len(self.noise_items),
            "status_counts": dict(sorted(status_counts.items())),
            "interest_tag_counts": dict(sorted(tag_counts.items())),
        }

    def to_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "items": [item.to_payload() for item in self.items],
            "noise_items": [item.to_payload() for item in self.noise_items],
        }
