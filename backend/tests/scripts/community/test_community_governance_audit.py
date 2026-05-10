from __future__ import annotations

from collections import Counter

from app.services.hotpost.hotpost_community_activity import (
    CommunityActivity,
    CommunityPoolSnapshot,
    SupplyCommunitySnapshot,
)
from scripts.community.community_governance_audit import (
    classify,
    is_low_priority_stale,
    promotion_band,
    slice_noise,
)


def test_hotpost_verified_missing_pool_promotes_candidate() -> None:
    item = CommunityActivity(community_name="r/ClaudeCode", name_key="claudecode")
    item.card_count = 2

    assert classify(item, None) == "promote_candidate"


def test_pool_without_hotpost_or_supply_is_stale_review() -> None:
    item = CommunityActivity(community_name="r/OldPool", name_key="oldpool")
    item.pool = CommunityPoolSnapshot(name="r/OldPool")

    assert classify(item, None) == "stale_review"


def test_pool_discovered_without_hotpost_needs_evidence() -> None:
    item = CommunityActivity(community_name="r/babybumps", name_key="babybumps")
    item.pool = CommunityPoolSnapshot(name="r/babybumps")

    assert classify(item, "pending") == "needs_evidence"


def test_supply_without_hotpost_needs_evidence() -> None:
    item = CommunityActivity(community_name="r/mcp", name_key="mcp")
    item.supply = SupplyCommunitySnapshot(scopes=("ai-automation",))

    assert classify(item, None) == "needs_evidence"


def test_one_card_without_supply_or_discovery_is_observation_queue() -> None:
    item = CommunityActivity(community_name="r/VacuumCleaners", name_key="vacuumcleaners")
    item.card_count = 1

    assert classify(item, None) == "observation_queue"


def test_promotion_band_separates_strong_and_weak_promote() -> None:
    strong = CommunityActivity(community_name="r/PPC", name_key="ppc")
    strong.card_count = 37
    strong.supply = SupplyCommunitySnapshot(scopes=("business-growth-ops",))

    weak = CommunityActivity(community_name="r/codex", name_key="codex")
    weak.card_count = 3

    assert promotion_band(strong, None) == "strong"
    assert promotion_band(weak, None) == "weak"


def test_pet_slice_flags_ai_scope_as_noise() -> None:
    item = CommunityActivity(community_name="r/AI_Agents", name_key="ai_agents")
    item.card_count = 1
    item.source_scopes = Counter({"ai-automation": 1})

    assert slice_noise("pet-products", item) is True


def test_relationship_advice_is_excluded_from_first_stale_pass() -> None:
    item = CommunityActivity(
        community_name="r/relationship_advice",
        name_key="relationship_advice",
    )

    assert is_low_priority_stale(item) is True
