from __future__ import annotations

from app.services.crawl.execute_plan_deps_factory import (
    ExecuteCrawlPlanDepsFactoryInput,
    build_execute_crawl_plan_dispatch_deps,
)


async def _noop(*args, **kwargs):
    return None


def test_execute_plan_deps_factory_reuses_shared_crawler_factory() -> None:
    class DummyCrawler:
        pass

    deps = build_execute_crawl_plan_dispatch_deps(
        ExecuteCrawlPlanDepsFactoryInput(
            execute_patrol=_noop,
            execute_backfill_posts=_noop,
            execute_seed_archive=_noop,
            execute_probe=_noop,
            execute_backfill_comments=_noop,
            crawler_factory=DummyCrawler,
            resolve_post_context=_noop,
            count_existing_comments=_noop,
            persist_comments=_noop,
            classify_comments=_noop,
            extract_comment_entities=_noop,
        )
    )

    assert deps.execute_patrol is _noop
    assert deps.execute_backfill_posts is _noop
    assert deps.execute_seed_archive is _noop
    assert deps.build_patrol_deps().crawler_factory is DummyCrawler
    assert deps.build_backfill_posts_deps().crawler_factory is DummyCrawler
    assert deps.build_seed_archive_deps().crawler_factory is DummyCrawler


def test_execute_plan_deps_factory_builds_backfill_comment_deps() -> None:
    deps = build_execute_crawl_plan_dispatch_deps(
        ExecuteCrawlPlanDepsFactoryInput(
            execute_patrol=_noop,
            execute_backfill_posts=_noop,
            execute_seed_archive=_noop,
            execute_probe=_noop,
            execute_backfill_comments=_noop,
            crawler_factory=object,
            resolve_post_context=_noop,
            count_existing_comments=_noop,
            persist_comments=_noop,
            classify_comments=_noop,
            extract_comment_entities=_noop,
        )
    )

    comment_deps = deps.build_backfill_comments_deps()

    assert deps.execute_backfill_comments is _noop
    assert comment_deps.resolve_post_context is _noop
    assert comment_deps.count_existing_comments is _noop
    assert comment_deps.persist_comments is _noop
    assert comment_deps.classify_comments is _noop
    assert comment_deps.extract_comment_entities is _noop
