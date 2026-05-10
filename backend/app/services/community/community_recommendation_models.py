from __future__ import annotations

from dataclasses import dataclass, field

from app.services.hotpost.hotpost_community_activity import normalize_community_key


READY = "ready"
HISTORICAL_DEPTH = "historical_depth"
WATCHING = "watching"

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class CommunitySignal:
    community: str
    categories: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    semantic_terms: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    content_label_terms: tuple[str, ...] = ()
    content_entity_terms: tuple[str, ...] = ()
    semantic_observations: int = 0
    historical_posts: int = 0
    recent_posts_15d: int = 0
    latest_activity_at: str | None = None
    recent_activity_source: str | None = None
    hotpost_cards: int = 0
    content_labels: int = 0
    content_entities: int = 0
    quality_score: float = 0.0
    sample_titles: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return normalize_community_key(self.community)


@dataclass(frozen=True)
class CapabilityTag:
    tag_id: str
    name: str
    description: str
    group: str
    status: str
    user_input_required: bool
    keywords: tuple[str, ...]
    community_count: int
    ready_community_count: int
    historical_community_count: int
    watching_community_count: int
    generic_community_count: int
    longtail_community_count: int
    evidence_sources: tuple[str, ...]
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommunityRecommendation:
    community: str
    status: str
    role: str
    score: float
    reasons: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    risk_flags: tuple[str, ...]
    recent_posts_15d: int
    latest_activity_at: str | None
    historical_posts: int
    hotpost_cards: int
    semantic_observations: int
    semantic_terms: tuple[str, ...] = ()
    evidence_summary: tuple[str, ...] = ()
    sample_titles: tuple[str, ...] = ()
    best_for: str = ""
    activity_label: str = ""
    related_to: tuple[str, ...] = ()
    evidence_teaser: str = ""


@dataclass(frozen=True)
class PreviewAcceptance:
    ready_count: int
    historical_count: int
    watching_count: int
    generic_count: int
    longtail_count: int
    db_writes: bool = False
    user_input_required: bool = False
    passed: bool = False
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecommendationPreview:
    tags: tuple[CapabilityTag, ...]
    recommendations: dict[str, tuple[CommunityRecommendation, ...]] = field(default_factory=dict)
    acceptance: PreviewAcceptance = field(
        default_factory=lambda: PreviewAcceptance(
            ready_count=0,
            historical_count=0,
            watching_count=0,
            generic_count=0,
            longtail_count=0,
            blockers=("no_recommendations",),
        )
    )


@dataclass(frozen=True)
class CommunityActivitySnapshot:
    community: str
    recent_posts_15d: int
    latest_activity_at: str | None = None
    source: str = "activity_probe"
