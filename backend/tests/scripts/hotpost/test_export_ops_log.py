from __future__ import annotations

from scripts.hotpost.export_ops_log import build_recent_publish_days, render_day_markdown, render_index_markdown


def _card(
    *,
    card_id: str,
    published_at: str,
    lane: str,
    card_type: str,
    title: str,
    scope_id: str,
    scope_name: str,
    topic_pack_id: str,
    top_community: str | None = None,
) -> dict:
    return {
        "card_id": card_id,
        "published_at": published_at,
        "lane": lane,
        "card_type": card_type,
        "title": title,
        "source_scope_id": scope_id,
        "source_scope_name": scope_name,
        "topic_pack_id": topic_pack_id,
        "top_community": top_community,
    }


def test_build_recent_publish_days_groups_by_local_day() -> None:
    cards = [
        _card(
            card_id="card-1",
            published_at="2026-04-20T16:30:00Z",
            lane="signal",
            card_type="validate",
            title="夜里发的卡",
            scope_id="ecommerce-sellers",
            scope_name="电商与卖家",
            topic_pack_id="selection-signals",
        ),
        _card(
            card_id="card-2",
            published_at="2026-04-20T10:00:00Z",
            lane="hot",
            card_type="validate",
            title="白天发的卡",
            scope_id="business-growth-ops",
            scope_name="商业增长与运营",
            topic_pack_id="paid-economics",
        ),
    ]

    publish_days = build_recent_publish_days(cards, days=2, timezone="Asia/Shanghai")

    assert [item.day for item in publish_days] == ["2026-04-21", "2026-04-20"]
    assert [card["card_id"] for card in publish_days[0].cards] == ["card-1"]
    assert publish_days[1].lane_counts["hot"] == 1


def test_render_markdown_contains_structure_and_scope() -> None:
    cards = [
        _card(
            card_id="card-1",
            published_at="2026-04-21T01:00:00Z",
            lane="signal",
            card_type="validate",
            title="选品需求卡",
            scope_id="ecommerce-sellers",
            scope_name="电商与卖家",
            topic_pack_id="selection-signals",
            top_community="r/Shopify",
        ),
        _card(
            card_id="card-2",
            published_at="2026-04-21T02:00:00Z",
            lane="breakdown",
            card_type="write",
            title="AI 工作流长文",
            scope_id="ai-automation",
            scope_name="AI 与自动化",
            topic_pack_id="agent-builder",
        ),
    ]

    publish_days = build_recent_publish_days(cards, days=1, timezone="Asia/Shanghai")
    index_markdown = render_index_markdown(publish_days, timezone="Asia/Shanghai")
    day_markdown = render_day_markdown(publish_days[0])

    assert "运营日志" in index_markdown
    assert "[查看](2026-04-21.md)" in index_markdown
    assert "结构分布" in day_markdown
    assert "signal / validate" in day_markdown
    assert "breakdown / write" in day_markdown
    assert "电商与卖家" in day_markdown
    assert "agent-builder" in day_markdown
    assert "主社区" in day_markdown
    assert "r/Shopify" in day_markdown


def test_scope_summary_uses_display_name_order() -> None:
    cards = [
        _card(
            card_id="card-ai",
            published_at="2026-04-21T01:00:00Z",
            lane="signal",
            card_type="validate",
            title="AI 工作流",
            scope_id="ai-automation",
            scope_name="AI 与自动化",
            topic_pack_id="agent-builder",
        ),
        _card(
            card_id="card-growth",
            published_at="2026-04-21T02:00:00Z",
            lane="signal",
            card_type="validate",
            title="增长投放",
            scope_id="business-growth-ops",
            scope_name="商业增长与运营",
            topic_pack_id="paid-economics",
        ),
    ]

    publish_days = build_recent_publish_days(cards, days=1, timezone="Asia/Shanghai")
    day_markdown = render_day_markdown(publish_days[0])

    assert "- 类别分布：`商业增长与运营 1 / AI 与自动化 1`" in day_markdown
