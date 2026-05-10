from app.services.hotpost.reddit_acquisition import (
    build_reddit_acquisition_plan,
    resolve_comment_post_limit,
    should_expand_acquisition,
)


def test_build_reddit_acquisition_plan_uses_light_scout_then_expand() -> None:
    plan = build_reddit_acquisition_plan(
        mode="opportunity",
        query_parts=["invoice automation", "billing workflow"],
        subreddits=["r/saas", "r/startups", "r/entrepreneur"],
        limit=10,
        max_posts_per_search=30,
    )

    assert [job.query_part for job in plan.scout.jobs] == [
        "invoice automation",
        "invoice automation",
    ]
    assert [job.subreddit for job in plan.scout.jobs] == [
        "r/saas",
        "r/startups",
    ]
    assert plan.scout.max_posts == 20
    assert plan.expand is not None
    assert len(plan.expand.jobs) == 4
    assert should_expand_acquisition(plan=plan, filtered_posts=3, limit=10) is True


def test_build_reddit_acquisition_plan_global_search_only_expands_when_needed() -> None:
    plan = build_reddit_acquisition_plan(
        mode="trending",
        query_parts=["robot vacuum", "apartment cleaning"],
        subreddits=None,
        limit=8,
        max_posts_per_search=12,
    )

    assert [job.query_part for job in plan.scout.jobs] == ["robot vacuum"]
    assert [job.subreddit for job in plan.scout.jobs] == [None]
    assert plan.expand is not None
    assert [job.query_part for job in plan.expand.jobs] == ["apartment cleaning"]
    assert should_expand_acquisition(plan=plan, filtered_posts=8, limit=8) is False


def test_build_reddit_acquisition_plan_lets_rant_probe_two_subreddits_first() -> None:
    plan = build_reddit_acquisition_plan(
        mode="rant",
        query_parts=["shopify plugin complaints"],
        subreddits=["r/customerservice", "r/smallbusiness", "r/rant"],
        limit=6,
        max_posts_per_search=30,
    )

    assert [job.subreddit for job in plan.scout.jobs] == ["r/customerservice", "r/smallbusiness"]
    assert plan.scout.max_posts == 12
    assert plan.expand is not None


def test_resolve_comment_post_limit_caps_high_volume_rant_comment_fetch() -> None:
    assert (
        resolve_comment_post_limit(
            mode="rant",
            evidence_count=20,
            max_comment_posts=12,
        )
        == 5
    )


def test_resolve_comment_post_limit_keeps_non_rant_budget_unchanged() -> None:
    assert (
        resolve_comment_post_limit(
            mode="trending",
            evidence_count=20,
            max_comment_posts=8,
        )
        == 8
    )
