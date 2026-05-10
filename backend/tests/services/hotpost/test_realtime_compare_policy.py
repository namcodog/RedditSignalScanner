from app.schemas.hotpost import HotpostQueryParse, HotpostSearchRequest
from app.services.hotpost.realtime_compare_policy import (
    build_query_resolution_from_override,
    resolve_realtime_compare_policy,
)


def test_resolve_realtime_compare_policy_only_for_rant_compare_with_pair() -> None:
    request = HotpostSearchRequest(
        query="为什么选 Codex 不选 Claude",
        mode="rant",
        query_parse_override=HotpostQueryParse(
            query_kind="compare",
            subject="Codex",
            compare_target="Claude",
            focus="长指令",
            scenario="AI coding",
        ),
    )

    policy = resolve_realtime_compare_policy(mode="rant", request=request)

    assert policy is not None
    assert policy.initial_query_parts_limit_cap == 2
    assert policy.max_comment_posts_cap == 6
    assert policy.disable_reasoning_retry is True


def test_resolve_realtime_compare_policy_ignores_non_compare_requests() -> None:
    request = HotpostSearchRequest(query="为什么 Notion AI 总把我的笔记改写成空话", mode="rant")

    assert resolve_realtime_compare_policy(mode="rant", request=request) is None


def test_build_query_resolution_from_override_uses_confirmed_tags() -> None:
    resolution = build_query_resolution_from_override(
        request_query="为什么做 repo 级编码时不少人会选 Codex 不选 Claude",
        query_parse=HotpostQueryParse(
            query_kind="compare",
            subject="Codex",
            compare_target="Claude",
            focus="repo级编码",
            scenario="AI coding",
        ),
    )

    assert resolution.search_query.startswith("Codex vs Claude")
    assert "repo" in resolution.search_query
    assert "coding" in resolution.search_query
    assert resolution.keywords[:2] == ["Codex", "Claude"]
    assert "repo级编码" in resolution.keywords
    assert "AI coding" in resolution.keywords
    assert "repo" in resolution.keywords
    assert "coding" in resolution.keywords
    assert resolution.source == "original"


def test_build_query_resolution_from_override_expands_focus_bundle_terms() -> None:
    resolution = build_query_resolution_from_override(
        request_query="为什么大家说 Codex 比 Claude 更能听懂长指令",
        query_parse=HotpostQueryParse(
            query_kind="compare",
            subject="Codex",
            compare_target="Claude",
            focus="听懂长指令",
            scenario="AI coding",
        ),
    )

    assert resolution.search_query.startswith("Codex vs Claude")
    assert "instruction following" in resolution.keywords
    assert "long instruction" in resolution.keywords
