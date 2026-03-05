from app.services.analysis.deduplicator import deduplicate_posts_by_embeddings


def test_deduplicate_posts_by_embeddings_merges_similar_vectors() -> None:
    posts = [
        {
            "id": "p1",
            "title": "alpha",
            "summary": "alpha",
            "score": 10,
            "num_comments": 2,
        },
        {
            "id": "p2",
            "title": "beta",
            "summary": "beta",
            "score": 1,
            "num_comments": 1,
        },
    ]
    embeddings = {
        "p1": [1.0, 0.0],
        "p2": [0.99, 0.01],
    }

    deduped = deduplicate_posts_by_embeddings(posts, embeddings, threshold=0.95)

    assert len(deduped) == 1
    assert "p2" in deduped[0]["duplicate_ids"]


def test_deduplicate_posts_by_embeddings_keeps_missing_vectors() -> None:
    posts = [
        {"id": "p1", "title": "alpha", "summary": "alpha"},
        {"id": "p2", "title": "beta", "summary": "beta"},
    ]
    embeddings = {"p1": [1.0, 0.0]}

    deduped = deduplicate_posts_by_embeddings(posts, embeddings, threshold=0.95)

    assert len(deduped) == 2
