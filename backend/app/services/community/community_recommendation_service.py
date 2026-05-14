from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.community.community_brand_evidence import (
    CommunityBrandEvidence,
    load_community_brand_evidence,
    merge_community_brand_evidence,
)
from app.services.community.community_recommendation_audit import (
    RecommendationAudit,
    audit_to_payload,
    build_recommendation_audit,
)
from app.services.community.community_recommendation_builder import build_preview
from app.services.community.community_recommendation_core import (
    merge_activity_snapshots,
)
from app.services.community.community_recommendation_loader import (
    load_community_signals,
)
from app.services.community.community_recommendation_models import (
    CommunityActivitySnapshot,
    CommunitySignal,
    JsonValue,
    RecommendationPreview,
)
from app.services.community.community_recommendation_payload import preview_to_payload
from app.services.community.interest_tag_catalog import (
    InterestTagCatalog,
    load_interest_tag_catalog,
)
from app.services.hotpost.hotpost_community_activity import (
    HotpostCommunityActivityProvider,
)


@dataclass(frozen=True)
class CommunityRecommendationReport:
    preview: RecommendationPreview
    audit: RecommendationAudit

    @property
    def recommendation_count(self) -> int:
        return sum(len(items) for items in self.preview.recommendations.values())

    @property
    def summary(self) -> dict[str, JsonValue]:
        return {
            "tags": len(self.preview.tags),
            "recommendations": self.recommendation_count,
            "acceptance_passed": self.preview.acceptance.passed,
            "ready_count": self.preview.acceptance.ready_count,
            "db_writes": self.preview.acceptance.db_writes,
            "user_input_required": self.preview.acceptance.user_input_required,
            "audit_rows": self.audit.row_count,
        }

    def preview_payload(self) -> dict[str, JsonValue]:
        return preview_to_payload(self.preview)

    def audit_payload(self) -> dict[str, JsonValue]:
        return cast(dict[str, JsonValue], audit_to_payload(self.audit))


def build_community_recommendation_report_from_signals(
    signals: Iterable[CommunitySignal],
    *,
    brand_evidence: Iterable[CommunityBrandEvidence] = (),
    tag_limit: int = 10,
    community_limit: int = 20,
    catalog: InterestTagCatalog | None = None,
) -> CommunityRecommendationReport:
    active_catalog = catalog or load_interest_tag_catalog()
    merged = merge_community_brand_evidence(signals, brand_evidence)
    preview = build_preview(
        merged,
        tag_limit=tag_limit,
        community_limit=community_limit,
        catalog=active_catalog,
    )
    return CommunityRecommendationReport(
        preview=preview,
        audit=build_recommendation_audit(preview, catalog=active_catalog),
    )


async def build_community_recommendation_report(
    session: AsyncSession,
    *,
    tag_limit: int = 10,
    community_limit: int = 20,
    activity_snapshots: Iterable[CommunityActivitySnapshot] = (),
    activity_provider: HotpostCommunityActivityProvider | None = None,
    include_brand_evidence: bool = True,
    catalog: InterestTagCatalog | None = None,
) -> CommunityRecommendationReport:
    signals = await load_community_signals(session, activity_provider=activity_provider)
    merged = merge_activity_snapshots(signals, activity_snapshots)
    brand_evidence = (
        await load_community_brand_evidence(session) if include_brand_evidence else ()
    )
    return build_community_recommendation_report_from_signals(
        merged,
        brand_evidence=brand_evidence,
        tag_limit=tag_limit,
        community_limit=community_limit,
        catalog=catalog,
    )
