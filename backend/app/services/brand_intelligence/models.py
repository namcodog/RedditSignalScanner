from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BrandEvidence:
    card_id: str
    community: str
    source: str
    source_text: str
    observed_at: str
    permalink: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "card_id": self.card_id,
            "community": self.community,
            "source": self.source,
            "source_text": self.source_text,
            "observed_at": self.observed_at,
        }
        if self.permalink:
            payload["permalink"] = self.permalink
        return payload


@dataclass
class BrandCandidate:
    canonical_name: str
    status: str = "candidate"
    source_lifecycle: str = "approved"
    matched_terms: set[str] = field(default_factory=set)
    communities: set[str] = field(default_factory=set)
    evidence: list[BrandEvidence] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "status": self.status,
            "source_lifecycle": self.source_lifecycle,
            "matched_terms": sorted(self.matched_terms, key=str.lower),
            "mention_count": len(self.evidence),
            "community_count": len(self.communities),
            "communities": sorted(self.communities, key=str.lower),
            "semantic_known": True,
            "evidence": [item.to_payload() for item in self.evidence],
        }


@dataclass(frozen=True)
class BrandDigestReport:
    report_date: str
    card_count: int
    brands: tuple[BrandCandidate, ...]

    def to_payload(self) -> dict[str, object]:
        evidence_count = sum(len(item.evidence) for item in self.brands)
        return {
            "summary": {
                "report_date": self.report_date,
                "source": "hotpost_published_cards",
                "db_writes": False,
                "card_count": self.card_count,
                "brand_count": len(self.brands),
                "evidence_count": evidence_count,
            },
            "brands": [item.to_payload() for item in self.brands],
        }
