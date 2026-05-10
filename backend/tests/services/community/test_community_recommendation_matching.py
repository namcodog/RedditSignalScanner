from __future__ import annotations

from app.services.community.community_recommendation_preview import (
    CommunitySignal,
    build_capability_tags,
    build_recommendations_for_tag,
)
from app.services.community.interest_tag_catalog import (
    InterestTagCatalog,
    InterestTagDefinition,
    load_interest_tag_catalog,
)


def test_category_match_requires_topic_evidence_not_category_only() -> None:
    catalog = InterestTagCatalog(
        tags=(
            InterestTagDefinition(
                tag_id="fixture_tag",
                display_name="Fixture Tag",
                short_description="Fixture description",
                group="Fixture Group",
                source_refs=("topic_cluster:fixture",),
                source_ref_match=False,
                category_keys=("legacy_bucket",),
                keyword_keys=("expected",),
                semantic_keys=("expected",),
            ),
        ),
        policy=load_interest_tag_catalog().policy,
    )
    signals = [
        CommunitySignal(
            community="r/unrelated",
            categories=("legacy_bucket",),
            hotpost_cards=3,
            sample_titles=("unrelated evidence",),
        )
    ]

    tag = build_capability_tags(signals, catalog=catalog)[0]

    assert tag.community_count == 0
    assert build_recommendations_for_tag(tag, signals, catalog=catalog) == ()
