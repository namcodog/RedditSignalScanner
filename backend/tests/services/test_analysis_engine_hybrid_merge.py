from app.services.analysis.analysis_engine import _merge_posts_by_id


def test_merge_posts_by_id_skips_duplicates() -> None:
    primary = [{"id": "1"}, {"id": "2"}]
    extra = [{"id": "2"}, {"id": "3"}]

    merged = _merge_posts_by_id(primary, extra)

    assert len(merged) == 3
    assert merged[-1]["id"] == "3"
