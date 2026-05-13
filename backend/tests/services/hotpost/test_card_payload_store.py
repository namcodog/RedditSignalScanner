from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def _seeded_path(tmp_path: Path) -> Path:
    path = tmp_path / "hotpost_cards.json"
    path.write_text('{"categories":[],"candidates":[],"drafts":[],"published":[]}', encoding="utf-8")
    return path


def _candidate(candidate_id: str, post_id: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "signal_id": f"sig-{candidate_id}",
        "source_scope_id": "business-growth-ops",
        "source_scope_name": "商业增长与运营",
        "query": "offline conversions roas",
        "matched_subreddit": "PPC",
        "post_id": post_id,
        "title": f"title-{candidate_id}",
        "score": 10,
        "num_comments": 4,
        "created_at": "2026-04-08T00:00:00Z",
        "collected_at": "2026-04-08T00:00:00Z",
        "collect_batch_id": "batch-1",
        "topic_pack_id": "paid-economics",
        "time_window": "7d",
        "signal_level": "rising",
        "why_now_reason": "recurring_7d",
        "listing_source": "search:relevance:week",
        "primary_reason": "paid-economics:test",
        "matched_keywords": ["offline conversions"],
        "top_communities": ["r/PPC"],
        "thread_count": 2,
        "community_count": 2,
        "quote_count": 2,
        "intent_tags": ["趋势变化"],
        "evidence_quotes": [
            {
                "text": "We switched the account to optimize for offline deals and ROAS collapsed.",
                "community": "r/PPC",
                "permalink": f"https://www.reddit.com/r/PPC/comments/{post_id}/q1",
            },
            {
                "text": "The algorithm only had a handful of qualified conversions to learn from.",
                "community": "r/PPC",
                "permalink": f"https://www.reddit.com/r/PPC/comments/{post_id}/q2",
            },
        ],
    }


def test_narrow_readers_follow_split_layout(monkeypatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_payload_store import (
        load_candidates,
        load_categories,
        load_drafts,
        load_published_cards,
        write_cards_payload,
    )

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
        "candidates": [_candidate("cand-a", "post-a")],
        "drafts": [{"draft_id": "draft-a", "card_id": "card-a", "card_type": "validate"}],
        "published": [{"card_id": "card-pub", "published_at": "2026-04-09T00:00:00Z"}],
    }

    write_cards_payload(payload)

    assert load_categories()[0]["category_id"] == "all"
    assert load_candidates()[0]["candidate_id"] == "cand-a"
    assert load_drafts()[0]["draft_id"] == "draft-a"
    assert load_published_cards()[0]["card_id"] == "card-pub"


def test_publish_draft_keeps_payload_valid_under_concurrent_writes(monkeypatch, tmp_path: Path) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.schemas.hotpost_clues import ValidationDetail
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_candidate_store import save_candidate
    from app.services.hotpost.card_draft_builder import seed_validation_draft
    from app.services.hotpost.card_draft_store import publish_draft, save_draft
    from app.services.hotpost.card_storage_layout import storage_root_for

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    draft_ids: list[str] = []
    for candidate_id, post_id in (("cand-a", "post-a"), ("cand-b", "post-b")):
        candidate = CandidatePack.model_validate(_candidate(candidate_id, post_id))
        save_candidate(candidate)
        draft = seed_validation_draft(candidate).model_copy(
            update={
                "title": f"published-{candidate_id}",
                "summary_line": f"summary-{candidate_id}",
                "audience": "投手",
                "why_now": "最近这类讨论开始影响预算判断。",
                "source_link": f"https://www.reddit.com/r/PPC/comments/{post_id}",
                "detail": ValidationDetail(
                    pain_point="优化目标一改，投放表现立刻失稳。",
                    target_user_and_scene="小预算广告账户切换主要优化目标时。",
                    why_test_now="最近讨论已经从参数设置转向预算判断。",
                    min_test_action="先核对主要优化目标切换前后的样本量。",
                    continue_signal="继续有人反馈样本回传太少导致系统学歪。",
                    stop_signal="如果回传样本恢复稳定且表现回升，这个信号就减弱。",
                ),
            }
        )
        save_draft(draft)
        draft_ids.append(draft.draft_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(publish_draft, draft_ids))

    payload = card_payload_store.load_cards_payload()
    assert len(results) == 2
    assert len(payload["drafts"]) == 0
    assert len(payload["published"]) == 2
    assert {item["card_id"] for item in payload["published"]} == {card_id for card_id, _ in results}

    root = storage_root_for(path)
    latest = json.loads((root / "releases" / "latest.json").read_text(encoding="utf-8"))
    release_root = root / "releases" / latest["release_id"]
    index = json.loads((release_root / "index.json").read_text(encoding="utf-8"))
    assert index["card_count"] == 2
    assert sorted(index["card_ids"]) == sorted(card_id for card_id, _ in results)
    assert (root / "candidates" / "business-growth-ops.json").exists()


def test_merge_published_cards_preserves_other_states(monkeypatch, tmp_path: Path) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.schemas.hotpost_clues import ValidationDetail
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_candidate_store import save_candidate
    from app.services.hotpost.card_draft_builder import seed_validation_draft
    from app.services.hotpost.card_draft_store import publish_draft, save_draft
    from app.services.hotpost.card_payload_store import load_cards_payload, load_published_cards, merge_published_cards

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    first_candidate = CandidatePack.model_validate(_candidate("cand-a", "post-a"))
    save_candidate(first_candidate)
    draft = seed_validation_draft(first_candidate).model_copy(
        update={
            "title": "published-cand-a",
            "summary_line": "summary-a",
            "audience": "投手",
            "why_now": "最近这类讨论开始影响预算判断。",
            "source_link": "https://www.reddit.com/r/PPC/comments/post-a",
            "detail": ValidationDetail(
                pain_point="优化目标一改，投放表现立刻失稳。",
                target_user_and_scene="小预算广告账户切换主要优化目标时。",
                why_test_now="最近讨论已经从参数设置转向预算判断。",
                min_test_action="先核对主要优化目标切换前后的样本量。",
                continue_signal="继续有人反馈样本回传太少导致系统学歪。",
                stop_signal="如果回传样本恢复稳定且表现回升，这个信号就减弱。",
            ),
        }
    )
    save_draft(draft)
    card_id, _ = publish_draft(draft.draft_id)

    stale_published = list(load_published_cards())

    second_candidate = CandidatePack.model_validate(_candidate("cand-b", "post-b"))
    save_candidate(second_candidate)

    updated_card = dict(stale_published[0])
    updated_card["summary_line"] = "summary-after-polish"
    touched = merge_published_cards([updated_card])

    payload = load_cards_payload()
    assert touched == 1
    assert payload["published"][0]["card_id"] == card_id
    assert payload["published"][0]["summary_line"] == "summary-after-polish"
    assert {item["candidate_id"] for item in payload["candidates"]} == {"cand-a", "cand-b"}


def test_publish_hot_draft_requires_controversy_chart(monkeypatch, tmp_path: Path) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_candidate_store import save_candidate
    from app.services.hotpost.card_draft_builder import seed_validation_draft
    from app.services.hotpost.card_draft_store import publish_draft, save_draft
    import app.services.hotpost.card_draft_builder as draft_builder

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    candidate = CandidatePack.model_validate(_candidate("cand-hot", "post-hot"))
    save_candidate(candidate)
    draft = seed_validation_draft(candidate).model_copy(
        update={
            "lane": "hot",
            "title": "这帖火在卖家都来报数",
            "summary_line": "评论区已经出现明确对线。",
            "audience": "独立站卖家",
            "why_now": "最近大家开始把销量腰斩当成共性问题。",
            "source_link": "https://www.reddit.com/r/PPC/comments/post-hot",
            "detail": {
                "flashpoint": "销量腰斩把一群卖家都炸出来了。",
                "fight_line": "是继续加广告，还是先停动作查老客流失。",
                "why_test_now": "评论区已经开始围绕先做哪一步起争执。",
                "continue_signal": "继续看有没有更多人给出相反做法。",
                "stop_signal": "如果讨论只剩抱怨没有分歧，这个热点就该停。",
            },
        }
    )
    save_draft(draft)

    monkeypatch.setattr(
        draft_builder,
        "refresh_hot_controversy_cards_sync",
        lambda cards: [
            {
                **cards[0],
                "controversy_chart": {
                    "support_ratio": 0.45,
                    "oppose_ratio": 0.35,
                    "neutral_ratio": 0.2,
                    "support_point": "先把老客拉回来",
                    "oppose_point": "先别停投流动作",
                    "neutral_point": "先看是不是季节波动",
                    "debate_focus": "销量腰斩后到底先救投放还是先救老客",
                    "dominant_side": "support",
                    "confidence": "medium",
                },
                "controversy_meta": {
                    "post_id": "post-hot",
                    "sample_size": 18,
                    "sampled_at": "2026-04-16T00:00:00Z",
                    "fetch_status": "ok",
                    "llm_summary_version": "cn_human_point_slots_v8",
                    "sample_quality": "enough",
                    "summary_status": "ok",
                    "confidence_reason": "样本够看出两边分歧",
                },
            }
        ],
    )

    card_id, _ = publish_draft(draft.draft_id)
    published = card_payload_store.load_published_cards()
    item = next(card for card in published if card["card_id"] == card_id)
    assert item["lane"] == "hot"
    assert item["controversy_chart"]["debate_focus"] == "销量腰斩后到底先救投放还是先救老客"
    assert item["controversy_meta"]["summary_status"] == "ok"


def test_publish_hot_draft_fails_without_controversy_chart(monkeypatch, tmp_path: Path) -> None:
    from app.schemas.hotpost_card_candidates import CandidatePack
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_candidate_store import save_candidate
    from app.services.hotpost.card_draft_builder import seed_validation_draft
    from app.services.hotpost.card_draft_store import publish_draft, save_draft
    import app.services.hotpost.card_draft_builder as draft_builder

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    candidate = CandidatePack.model_validate(_candidate("cand-hot-fail", "post-hot-fail"))
    save_candidate(candidate)
    draft = seed_validation_draft(candidate).model_copy(
        update={
            "lane": "hot",
            "title": "这帖火在卖家都来报数",
            "summary_line": "评论区已经出现明确对线。",
            "audience": "独立站卖家",
            "why_now": "最近大家开始把销量腰斩当成共性问题。",
            "source_link": "https://www.reddit.com/r/PPC/comments/post-hot-fail",
            "detail": {
                "flashpoint": "销量腰斩把一群卖家都炸出来了。",
                "fight_line": "是继续加广告，还是先停动作查老客流失。",
                "why_test_now": "评论区已经开始围绕先做哪一步起争执。",
                "continue_signal": "继续看有没有更多人给出相反做法。",
                "stop_signal": "如果讨论只剩抱怨没有分歧，这个热点就该停。",
            },
        }
    )
    save_draft(draft)

    monkeypatch.setattr(
        draft_builder,
        "refresh_hot_controversy_cards_sync",
        lambda cards: [{**cards[0], "controversy_meta": {"summary_status": "no_sample"}}],
    )

    try:
        publish_draft(draft.draft_id)
    except ValueError as exc:
        assert "controversy chart" in str(exc)
    else:
        raise AssertionError("expected hot publish to fail when controversy chart is missing")


def test_mutate_candidates_preserves_other_states(monkeypatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_payload_store import load_cards_payload, mutate_candidates, write_cards_payload

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
        "candidates": [_candidate("cand-a", "post-a")],
        "drafts": [{"draft_id": "draft-a", "card_id": "card-a", "card_type": "validate"}],
        "published": [{"card_id": "card-pub", "published_at": "2026-04-09T00:00:00Z"}],
    }
    write_cards_payload(payload)

    mutate_candidates(lambda candidates: candidates.append(_candidate("cand-b", "post-b")))

    current = load_cards_payload()
    assert {item["candidate_id"] for item in current["candidates"]} == {"cand-a", "cand-b"}
    assert current["drafts"] == payload["drafts"]
    assert current["published"] == payload["published"]


def test_mutate_drafts_preserves_other_states(monkeypatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_payload_store import load_cards_payload, mutate_drafts, write_cards_payload

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
        "candidates": [_candidate("cand-a", "post-a")],
        "drafts": [{"draft_id": "draft-a", "card_id": "card-a", "card_type": "validate"}],
        "published": [{"card_id": "card-pub", "published_at": "2026-04-09T00:00:00Z"}],
    }
    write_cards_payload(payload)

    mutate_drafts(
        lambda drafts: drafts.append({"draft_id": "draft-b", "card_id": "card-b", "card_type": "write"})
    )

    current = load_cards_payload()
    assert {item["draft_id"] for item in current["drafts"]} == {"draft-a", "draft-b"}
    assert current["candidates"] == payload["candidates"]
    assert current["published"] == payload["published"]


def test_replace_published_cards_preserves_other_states(monkeypatch, tmp_path: Path) -> None:
    from app.services.hotpost import card_payload_store
    from app.services.hotpost.card_payload_store import load_cards_payload, replace_published_cards, write_cards_payload

    path = _seeded_path(tmp_path)
    monkeypatch.setattr(card_payload_store, "_CARDS_PATH", path)

    payload = {
        "categories": [{"category_id": "all", "title": "全部", "description": "全部卡片"}],
        "candidates": [_candidate("cand-a", "post-a")],
        "drafts": [{"draft_id": "draft-a", "card_id": "card-a", "card_type": "validate"}],
        "published": [{"card_id": "card-pub", "published_at": "2026-04-09T00:00:00Z"}],
    }
    write_cards_payload(payload)

    count = replace_published_cards([{"card_id": "card-next", "published_at": "2026-04-10T00:00:00Z"}])

    current = load_cards_payload()
    assert count == 1
    assert current["published"] == [{"card_id": "card-next", "published_at": "2026-04-10T00:00:00Z"}]
    assert current["candidates"] == payload["candidates"]
    assert current["drafts"] == payload["drafts"]
