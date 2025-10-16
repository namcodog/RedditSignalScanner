from app.models.community_pool import PendingCommunity

def test_pending_community_has_discovery_and_review_fields() -> None:
    # Verify required fields exist for warmup-period workflow traceability
    fields = {
        "discovered_from_task_id",
        "reviewed_by",
        "first_discovered_at",
        "last_discovered_at",
    }
    for name in fields:
        assert hasattr(PendingCommunity, name), f"Missing field: {name}"

