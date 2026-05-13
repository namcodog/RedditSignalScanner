from __future__ import annotations

from scripts.acceptance.run_open_question_live_acceptance import (
    DEFAULT_SMOKE_CASES,
    _extract_remediation_blockers,
    _is_clickable_reddit_url,
    _pick_titles,
    _should_stop_retrying,
    _validate_report_contract,
)


def test_default_smoke_cases_count_is_three() -> None:
    assert len(DEFAULT_SMOKE_CASES) == 3


def test_pick_titles_supports_dict_and_text_items() -> None:
    values = [
        {"title": "标题一"},
        {"description": "描述二"},
        "文本三",
        {"title": ""},
    ]
    assert _pick_titles(values) == ["标题一", "描述二", "文本三"]


def test_is_clickable_reddit_url_requires_http_and_reddit_domain() -> None:
    assert _is_clickable_reddit_url("https://www.reddit.com/r/stripe/comments/demo") is True
    assert _is_clickable_reddit_url("/r/stripe/comments/demo") is False
    assert _is_clickable_reddit_url("https://example.com/not-reddit") is False


def test_validate_report_contract_accepts_clean_payload() -> None:
    report_payload = {
        "sources": {"report_tier": "A_full", "analysis_blocked": ""},
        "report_markdown": (
            "### 回款延迟与冻结\n"
            "### 多平台回款节奏预警助手\n"
        ),
        "canonical_report_json": {
            "target_communities": ["r/stripe", "r/ecommerce"],
            "pain_points": [
                {
                    "title": "回款延迟与冻结",
                    "evidence_chain": [
                        {
                            "title": "Stripe payout pending for 5 days",
                            "url": "https://www.reddit.com/r/stripe/comments/demo1",
                        }
                    ],
                },
                {
                    "title": "退款手续费侵蚀利润",
                    "evidence_chain": [
                        {
                            "title": "Refund fee still charged",
                            "url": "https://www.reddit.com/r/ecommerce/comments/demo2",
                        }
                    ],
                },
                {
                    "title": "对账路径碎片化",
                    "evidence_chain": [
                        {
                            "title": "Reconcile across platforms is painful",
                            "url": "https://www.reddit.com/r/shopify/comments/demo3",
                        }
                    ],
                },
            ],
            "opportunities": [
                {
                    "title": "多平台回款节奏预警助手",
                    "evidence_chain": [
                        {
                            "title": "Stripe payout pending for 5 days",
                            "url": "https://www.reddit.com/r/stripe/comments/demo4",
                        }
                    ],
                },
                {
                    "title": "退款手续费可视化诊断助手",
                    "evidence_chain": [
                        {
                            "title": "Refund fee still charged",
                            "url": "https://www.reddit.com/r/ecommerce/comments/demo5",
                        }
                    ],
                },
            ],
        },
    }

    issues, summary = _validate_report_contract(
        report_payload=report_payload,
        required_tier="A_full",
        min_reddit_links=2,
    )

    assert issues == []
    assert summary["report_tier"] == "A_full"
    assert len(summary["pain_titles"]) == 3
    assert len(summary["opportunity_titles"]) == 2
    assert len(summary["reddit_links"]) >= 2


def test_validate_report_contract_rejects_placeholder_and_non_clickable_links() -> None:
    report_payload = {
        "sources": {"report_tier": "A_full", "analysis_blocked": ""},
        "report_markdown": "",
        "canonical_report_json": {
            "target_communities": ["r/stripe"],
            "pain_points": [
                {"title": "关键痛点 1", "evidence_chain": [{"title": "x", "url": "/r/stripe/comments/demo"}]},
            ],
            "opportunities": [
                {"title": "产品机会", "evidence_chain": [{"title": "x", "url": "/r/stripe/comments/demo"}]},
            ],
        },
    }

    issues, _ = _validate_report_contract(
        report_payload=report_payload,
        required_tier="A_full",
        min_reddit_links=2,
    )
    merged = "\n".join(issues)
    assert "placeholder pain title: 关键痛点 1" in merged
    assert "low-signal opportunity title: 产品机会" in merged
    assert "pain evidence has no clickable reddit link" in merged
    assert "opportunity evidence has no clickable reddit link" in merged


def test_extract_remediation_blockers_reads_budget_blocked_backfill() -> None:
    report_payload = {
        "sources": {
            "remediation_actions": [
                {
                    "type": "backfill_posts",
                    "targets": 0,
                    "blocked_reason": "budget_or_fuse_blocked",
                },
                {
                    "type": "backfill_comments",
                    "targets": 3,
                    "blocked_reason": "budget_or_fuse_blocked",
                },
            ]
        }
    }

    assert _extract_remediation_blockers(report_payload) == ["budget_or_fuse_blocked"]


def test_should_stop_retrying_for_manual_intervention() -> None:
    assert (
        _should_stop_retrying(
            blocked_reason="insufficient_samples",
            next_action="manual_intervention",
            remediation_blockers=[],
        )
        is True
    )


def test_should_stop_retrying_for_budget_blocked_insufficient_samples() -> None:
    assert (
        _should_stop_retrying(
            blocked_reason="insufficient_samples",
            next_action="",
            remediation_blockers=["budget_or_fuse_blocked"],
        )
        is True
    )


def test_should_not_stop_retrying_when_warmup_is_still_possible() -> None:
    assert (
        _should_stop_retrying(
            blocked_reason="insufficient_samples",
            next_action="wait_for_warmup",
            remediation_blockers=[],
        )
        is False
    )
