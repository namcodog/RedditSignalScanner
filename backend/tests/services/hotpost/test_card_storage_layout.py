from __future__ import annotations

import json
from pathlib import Path


def test_migrate_cards_payload_layout_splits_legacy_file(monkeypatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_storage_layout import storage_root_for

    legacy_path = tmp_path / "hotpost_cards.json"
    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部"}],
        "candidates": [
            {
                "candidate_id": "cand-1",
                "signal_id": "sig-1",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "query": "agent workflow",
                "matched_subreddit": "r/artificial",
                "post_id": "abc123",
                "title": "Agent workflow pain",
                "score": 100,
                "num_comments": 12,
                "created_at": "2026-04-08T00:00:00Z",
                "collected_at": "2026-04-08T00:00:00Z",
                "collect_batch_id": "batch-1",
                "topic_pack_id": "agent-builder",
                "time_window": "7d",
                "signal_level": "rising",
                "why_now_reason": "recurring_7d",
                "listing_source": "search:relevance:week",
                "primary_reason": "keyword",
                "matched_keywords": ["agent"],
                "top_communities": ["r/artificial"],
                "thread_count": 2,
                "community_count": 2,
                "quote_count": 2,
                "intent_tags": ["趋势变化"],
                "evidence_quotes": [],
            }
        ],
        "drafts": [
            {
                "draft_id": "draft-1",
                "card_id": "card-1",
                "signal_id": "sig-1",
                "card_type": "validate",
                "category_id": "validate",
                "source_scope_id": "ai-automation",
                "source_scope_name": "AI 与自动化",
                "source_domain_id": "artificial",
                "source_domain_name": "r/artificial",
                "title": "Draft title",
                "summary_line": "Draft summary",
                "audience": "开发者",
                "why_now": "Why now",
                "why_now_reason": "recurring_7d",
                "intent_tags": ["趋势变化"],
                "source_event_at": "2026-04-08T00:00:00Z",
                "source_module": {
                    "primary_communities": ["r/artificial"],
                    "top_community": "r/artificial",
                    "tone_tags": ["frustrated"],
                    "thread_count": 2,
                    "community_count": 2,
                    "last_active_text": "今天",
                },
                "preview_quote": {
                    "text": "preview",
                    "community": "r/artificial",
                    "permalink": "https://www.reddit.com/r/artificial/comments/abc123/q1",
                },
                "quotes": [],
                "source_link": "https://www.reddit.com/r/artificial/comments/abc123",
                "detail": {
                    "pain_point": "pain",
                    "target_user_and_scene": "scene",
                    "why_test_now": "now",
                    "min_test_action": "test",
                    "continue_signal": "continue",
                    "stop_signal": "stop",
                },
            }
        ],
        "published": [
            {
                "card_id": "card-2",
                "signal_id": "sig-2",
                "card_type": "write",
                "category_id": "write",
                "source_scope_id": "business-growth-ops",
                "source_scope_name": "商业增长与运营",
                "source_domain_id": "smallbusiness",
                "source_domain_name": "r/smallbusiness",
                "title": "Published title",
                "summary_line": "Published summary",
                "audience": "运营",
                "why_now": "Published why now",
                "why_now_reason": "recurring_7d",
                "intent_tags": ["趋势变化"],
                "source_event_at": "2026-04-08T00:00:00Z",
                "source_module": {
                    "primary_communities": ["r/smallbusiness"],
                    "top_community": "r/smallbusiness",
                    "tone_tags": ["urgent"],
                    "thread_count": 2,
                    "community_count": 2,
                    "last_active_text": "今天",
                },
                "preview_quote": {
                    "text": "preview",
                    "community": "r/smallbusiness",
                    "permalink": "https://www.reddit.com/r/smallbusiness/comments/def456/q1",
                },
                "quotes": [],
                "source_link": "https://www.reddit.com/r/smallbusiness/comments/def456",
                "published_at": "2026-04-08T00:00:00Z",
                "detail": {
                    "thesis": "thesis",
                    "writing_angle_or_perspective": "angle",
                    "tension_point_or_why_it_matters": "tension",
                    "title_hooks": ["hook"],
                    "quote_pack": ["quote"],
                },
            }
        ],
    }
    legacy_path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", legacy_path)

    result = card_payload_store.migrate_cards_payload_layout()
    root = storage_root_for(legacy_path)
    latest = json.loads((root / "releases" / "latest.json").read_text(encoding="utf-8"))

    assert result["categories"] == 1
    assert result["candidates"] == 1
    assert result["drafts"] == 1
    assert result["published"] == 1
    assert result["release_id"] == latest["release_id"]
    assert (root / "categories.json").exists()
    assert (root / "candidates" / "ai-automation.json").exists()
    assert (root / "drafts" / "draft-1.json").exists()
    assert (root / "releases" / latest["release_id"] / "cards" / "card-2.json").exists()

    loaded = card_payload_store.load_cards_payload()
    assert loaded["categories"][0]["category_id"] == "all"
    assert loaded["candidates"][0]["candidate_id"] == "cand-1"
    assert loaded["drafts"][0]["draft_id"] == "draft-1"
    assert loaded["published"][0]["card_id"] == "card-2"
