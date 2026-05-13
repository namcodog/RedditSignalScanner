from __future__ import annotations

from app.schemas.hotpost_clues import WritingCardDetail
from app.services.hotpost.breakdown_overlap_audit import audit_breakdown_overlap


def _card(card_id: str, *, scope: str, title: str, thesis: str, summary: str) -> WritingCardDetail:
    return WritingCardDetail.model_validate(
        {
            "card_id": card_id,
            "signal_id": card_id,
            "card_type": "write",
            "category_id": "write",
            "source_scope_id": scope,
            "source_scope_name": "测试",
            "source_domain_id": "hotpost",
            "source_domain_name": "Hotpost",
            "title": title,
            "summary_line": summary,
            "audience": "测试用户",
            "why_now": "测试 why now",
            "why_now_reason": "recurring_7d",
            "signal_level": "rising",
            "intent_tags": [],
            "top_community": "r/test",
            "thread_count": 2,
            "community_count": 2,
            "preview_quote": {"text": "q", "community": "r/test", "permalink": "https://reddit.com/1"},
            "published_at": "2026-04-08T00:00:00Z",
            "source_module": {"primary_communities": ["r/test"], "top_community": "r/test", "tone_tags": [], "thread_count": 2, "community_count": 2, "last_active_text": "近 7 天"},
            "quotes": [],
            "source_link": "https://reddit.com/1",
            "detail": {"thesis": thesis, "writing_angle_or_perspective": "", "tension_point_or_why_it_matters": "", "title_hooks": [], "quote_pack": []},
        }
    )


def test_breakdown_overlap_audit_flags_same_scope_high_overlap(monkeypatch) -> None:
    from app.services.hotpost import breakdown_overlap_audit as mod

    monkeypatch.setattr(
        mod,
        "load_cards_payload",
        lambda: {
            "published": [
                _card("a", scope="business-growth-ops", title="任务板装不下真实协作", thesis="任务板装不下真实协作，只能靠板外补丁接住推进。真实协作最后都回到轻量对齐。", summary="真实协作需要轻量对齐").model_dump(mode="json"),
                _card("b", scope="business-growth-ops", title="团队还是回到简单 roadmap 对齐", thesis="复杂工具过载，团队回到一页 roadmap 做轻量对齐推进，接住真实协作。", summary="轻量 roadmap 对齐比复杂工具更能接住真实协作").model_dump(mode="json"),
                _card("c", scope="ai-automation", title="AI 搜索把答案写顺了", thesis="答案越顺，核对成本越高。", summary="summary").model_dump(mode="json"),
            ]
        },
    )

    result = audit_breakdown_overlap(threshold=0.14)
    assert result["pair_count"] >= 1
