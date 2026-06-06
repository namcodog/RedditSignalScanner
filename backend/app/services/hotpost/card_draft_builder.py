from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.schemas.hotpost_clues import SourceModule, ValidationCardDetail, WritingCardDetail
from app.services.hotpost.card_lane_policy import infer_validation_lane, resolve_lane
from app.services.hotpost.hot_controversy_chart import refresh_hot_controversy_cards_sync
from app.schemas.hotpost_validate_details import empty_validation_detail_payload


def seed_validation_draft(candidate: CandidatePack) -> ValidationCardDraft:
    source_link = f"https://www.reddit.com/r/{candidate.matched_subreddit}/comments/{candidate.post_id}"
    lane = infer_validation_lane(candidate)
    return ValidationCardDraft(
        draft_id=f"draft-{candidate.candidate_id}-validate",
        candidate_id=candidate.candidate_id,
        candidate_ids=[candidate.candidate_id],
        card_id=f"card-{candidate.candidate_id}-validate",
        signal_id=candidate.signal_id,
        topic_pack_id=candidate.topic_pack_id,
        topic_cluster_id=candidate.topic_cluster_id,
        topic_cluster_ids=candidate.topic_cluster_ids,
        named_topic_ids=candidate.named_topic_ids,
        card_type="validate",
        lane=lane,
        category_id="validate",
        title=candidate.title,
        source_scope_id=candidate.source_scope_id,
        source_scope_name=candidate.source_scope_name,
        matched_subreddit=candidate.matched_subreddit,
        post_id=candidate.post_id,
        source_event_at=candidate.created_at,
        score=candidate.score,
        num_comments=candidate.num_comments,
        time_window=candidate.time_window,
        signal_level=candidate.signal_level,
        why_now_reason=candidate.why_now_reason,
        thread_count=candidate.thread_count,
        community_count=candidate.community_count,
        quote_count=candidate.quote_count,
        intent_tags=candidate.intent_tags,
        evidence_quotes=candidate.evidence_quotes,
        source_link=source_link,
        source_links=[source_link],
        source_communities=[f"r/{candidate.matched_subreddit}"],
        draft_note=f"Seeded from candidate {candidate.candidate_id}",
        detail=empty_validation_detail_payload(lane),
    )


def seed_writing_draft(candidate: CandidatePack) -> WritingCardDraft:
    source_link = f"https://www.reddit.com/r/{candidate.matched_subreddit}/comments/{candidate.post_id}"
    return WritingCardDraft(
        draft_id=f"draft-{candidate.candidate_id}-write",
        candidate_id=candidate.candidate_id,
        candidate_ids=[candidate.candidate_id],
        card_id=f"card-{candidate.candidate_id}-write",
        signal_id=candidate.signal_id,
        topic_pack_id=candidate.topic_pack_id,
        topic_cluster_id=candidate.topic_cluster_id,
        topic_cluster_ids=candidate.topic_cluster_ids,
        named_topic_ids=candidate.named_topic_ids,
        card_type="write",
        lane="breakdown",
        category_id="write",
        title=candidate.title,
        source_scope_id=candidate.source_scope_id,
        source_scope_name=candidate.source_scope_name,
        matched_subreddit=candidate.matched_subreddit,
        post_id=candidate.post_id,
        source_event_at=candidate.created_at,
        score=candidate.score,
        num_comments=candidate.num_comments,
        time_window=candidate.time_window,
        signal_level=candidate.signal_level,
        why_now_reason=candidate.why_now_reason,
        thread_count=candidate.thread_count,
        community_count=candidate.community_count,
        quote_count=candidate.quote_count,
        intent_tags=candidate.intent_tags,
        evidence_quotes=candidate.evidence_quotes,
        source_link=source_link,
        source_links=[source_link],
        source_communities=[f"r/{candidate.matched_subreddit}"],
        draft_note=f"Seeded from candidate {candidate.candidate_id}",
        detail={"thesis": "", "writing_angle_or_perspective": "", "tension_point_or_why_it_matters": "", "title_hooks": [], "quote_pack": []},
    )


def build_published_card(draft: ValidationCardDraft | WritingCardDraft) -> ValidationCardDetail | WritingCardDetail:
    _validate_review_content(draft)
    common = {
        "card_id": draft.card_id,
        "signal_id": draft.signal_id,
        "card_type": draft.card_type,
        "lane": resolve_lane(draft.lane, card_type=draft.card_type),
        "category_id": draft.category_id,
        "source_scope_id": draft.source_scope_id,
        "source_scope_name": draft.source_scope_name,
        "topic_pack_id": draft.topic_pack_id,
        "topic_cluster_id": draft.topic_cluster_id,
        "topic_cluster_ids": draft.topic_cluster_ids,
        "named_topic_ids": draft.named_topic_ids,
        "source_domain_id": draft.source_scope_id,
        "source_domain_name": draft.source_scope_name,
        "source_event_at": draft.source_event_at,
        "title": draft.title,
        "summary_line": draft.summary_line,
        "audience": draft.audience,
        "why_now": draft.why_now,
        "why_now_reason": draft.why_now_reason,
        "signal_level": draft.signal_level,
        "intent_tags": draft.intent_tags,
        "top_community": draft.source_communities[0],
        "thread_count": draft.thread_count,
        "community_count": draft.community_count,
        "preview_quote": draft.evidence_quotes[0],
        "published_at": datetime.now(timezone.utc),
        "source_module": SourceModule(primary_communities=draft.source_communities, top_community=draft.source_communities[0], tone_tags=[], thread_count=draft.thread_count, community_count=draft.community_count, last_active_text=_time_window_text(draft.time_window)),
        "quotes": draft.evidence_quotes,
        "source_link": draft.source_links[0],
    }
    if draft.card_type == "validate":
        published = ValidationCardDetail(**common, detail=draft.detail.model_dump())
        if published.lane == "hot":
            refreshed = refresh_hot_controversy_cards_sync([published.model_dump(mode="json")])[0]
            if not isinstance(refreshed.get("controversy_chart"), dict) or not isinstance(refreshed.get("controversy_meta"), dict):
                raise ValueError("Hot validate card requires controversy chart before publish")
            refreshed["controversy_meta"].pop("llm_trace", None)
            return ValidationCardDetail.model_validate(refreshed)
        return published
    return WritingCardDetail(**common, detail=draft.detail.model_dump())


def _validate_review_content(draft: ValidationCardDraft | WritingCardDraft) -> None:
    if not draft.evidence_quotes:
        raise ValueError("Draft requires evidence quotes before publish")
    required = [draft.summary_line, draft.audience, draft.why_now, draft.source_link]
    if any(not value.strip() for value in required):
        raise ValueError("Draft summary fields are incomplete")
    values = draft.detail.model_dump().values()
    if any((isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v) for v in values):
        raise ValueError("Draft detail fields are incomplete")


def _time_window_text(time_window: str) -> str:
    return {"24h": "近24小时", "7d": "近7天"}.get(time_window, "近30天")
