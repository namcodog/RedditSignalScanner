from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.schemas.community_governance import GovernancePoolCommunityItem
from app.services.crawl.crawl_plan import CrawlPlanBuilder


@pytest.mark.asyncio
async def test_build_plan_reads_truth_source_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    config_root.mkdir()
    (config_root / "community_blacklist.yaml").write_text("communities: []\n", encoding="utf-8")
    (config_root / "community_roles.yaml").write_text(
        yaml.safe_dump({"roles": {"buyer": {"communities": ["r/aitools"]}}}),
        encoding="utf-8",
    )
    (config_root / "vertical_overrides.yaml").write_text(
        yaml.safe_dump({"overrides": [{"subreddit": "r/aitools", "crawl_track": "posts_only"}]}),
        encoding="utf-8",
    )

    async def _fake_load(_session, *, is_config_blacklisted):
        return [
            GovernancePoolCommunityItem(
                id=1,
                name="r/aitools",
                tier="silver",
                priority="high",
                categories=["AI_Workflow"],
                normalized_categories=["AI_Workflow"],
                category_source="truth_source.membership",
                health_status="healthy",
                discovered_count=0,
                quality_score=0.88,
                is_active=True,
                is_blacklisted=False,
                config_blacklisted=is_config_blacklisted("r/aitools"),
                deleted_at=None,
            )
        ]

    monkeypatch.setattr(
        "app.services.crawl.crawl_plan.load_effective_truth_communities",
        _fake_load,
    )

    builder = CrawlPlanBuilder(db=None, config_root=config_root)  # type: ignore[arg-type]
    plan = await builder.build_plan()

    assert len(plan) == 1
    assert plan[0].profile.name == "r/aitools"
    assert plan[0].profile.categories == ["AI_Workflow"]
    assert plan[0].status == "active"
    assert plan[0].role == "buyer"
    assert plan[0].crawl_track == "posts_only"
    assert plan[0].source == "truth_source"


@pytest.mark.asyncio
async def test_build_plan_rejects_missing_required_projection_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_root = tmp_path / "config"
    config_root.mkdir()
    (config_root / "community_blacklist.yaml").write_text("communities: []\n", encoding="utf-8")
    (config_root / "community_roles.yaml").write_text("roles: {}\n", encoding="utf-8")
    (config_root / "vertical_overrides.yaml").write_text("overrides: []\n", encoding="utf-8")

    async def _fake_load(_session, *, is_config_blacklisted):
        return [
            GovernancePoolCommunityItem(
                id=1,
                name="r/broken",
                tier=None,
                priority="high",
                categories=["AI_Workflow"],
                normalized_categories=["AI_Workflow"],
                category_source="truth_source.membership",
                health_status="healthy",
                discovered_count=0,
                quality_score=0.91,
                is_active=True,
                is_blacklisted=False,
                config_blacklisted=is_config_blacklisted("r/broken"),
                deleted_at=None,
            )
        ]

    monkeypatch.setattr(
        "app.services.crawl.crawl_plan.load_effective_truth_communities",
        _fake_load,
    )

    builder = CrawlPlanBuilder(db=None, config_root=config_root)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="requires tier"):
        await builder.build_plan()
