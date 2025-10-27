from app.models.discovered_community import DiscoveredCommunity

def test_discovered_community_has_discovery_and_review_fields() -> None:
    # Verify required fields exist for warmup-period workflow traceability
    fields = {
        "discovered_from_task_id",
        "reviewed_by",
        "first_discovered_at",
        "last_discovered_at",
    }
    for name in fields:
        assert hasattr(DiscoveredCommunity, name), f"Missing field: {name}"
