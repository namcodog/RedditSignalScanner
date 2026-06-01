from __future__ import annotations

import json
import logging

import pytest

from app.schemas.hotpost_clues import QuotePreview
from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_validate_details import HotValidationDetail
from app.schemas.hotpost_validate_details import empty_validation_detail_payload
from app.services.hotpost.card_content_polish import (
    polish_generated_text,
    polish_published_card,
)
from app.services.hotpost.legacy_signal_copy_builder import (
    build_signal_why_now,
    build_signal_why_test_now,
)
from app.services.hotpost.card_content_generation_contract import (
    build_generation_field_contract_prompt,
)
from app.services.hotpost.card_content_generator import (
    _card_content_json_schema_for_draft,
    _generate_profile_semantic_brief,
    _generate_json,
    _semantic_brief_input,
    _semantic_brief_json_schema,
    _validated_text,
    generate_card_content,
    load_card_content_rules,
    load_card_content_models,
    refresh_breakdown_content,
    should_be_breakdown,
)
from app.services.hotpost.card_content_prompts import (
    build_breakdown_prompt,
    build_hot_prompt,
    build_signal_prompt,
)
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.semantic_readout import (
    finalize_signal_readout,
    finalize_validation_readout,
    semantic_prompt_extra,
)
from app.services.hotpost.signal_skill_variant_policy import all_banned_patterns


@pytest.fixture(autouse=True)
def _disable_production_profile_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOTPOST_CARD_CONTENT_PROFILE_ID", "off")
    load_card_content_models.cache_clear()
    yield
    load_card_content_models.cache_clear()


def _candidate(
    *,
    thread_count: int = 1,
    community_count: int = 1,
    quotes: list[dict] | None = None,
    **overrides,
) -> CandidatePack:
    payload = {
        "candidate_id": "cand-test-001",
        "signal_id": "sig-test-001",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 与自动化",
        "topic_pack_id": "agent-builder",
        "query": "crm",
        "matched_subreddit": "sales",
        "post_id": "abc123",
        "title": "Salesforce data entry is exhausting reps",
        "score": 48,
        "num_comments": 18,
        "created_at": "2026-04-05T00:00:00Z",
        "collected_at": "2026-04-05T00:00:00Z",
        "collect_batch_id": "batch-1",
        "time_window": "7d",
        "signal_level": "rising",
        "why_now_reason": "recurring_7d",
        "listing_source": "search:relevance:week",
        "primary_reason": "search_hit",
        "matched_keywords": ["crm"],
        "top_communities": ["r/sales"],
        "thread_count": thread_count,
        "community_count": community_count,
        "quote_count": len(quotes or []),
        "intent_tags": ["替换"],
        "evidence_quotes": quotes
        or [
            {
                "text": "I spend 30 min a day feeding Salesforce data.",
                "community": "r/sales",
                "permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            },
            {
                "text": "CRM updates feel like admin work for my manager, not me.",
                "community": "r/startups",
                "permalink": "https://www.reddit.com/r/startups/comments/def456/q2",
            },
            {
                "text": "We are already evaluating lighter alternatives.",
                "community": "r/sales",
                "permalink": "https://www.reddit.com/r/sales/comments/ghi789/q3",
            },
        ],
    }
    payload.update(overrides)
    return CandidatePack.model_validate(payload)


def _paid_econ_candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            "candidate_id": "cand-paid-econ-001",
            "signal_id": "sig-paid-econ-001",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "paid-economics",
            "query": "blended cac",
            "matched_subreddit": "PPC",
            "post_id": "ppc123",
            "title": "Lead Quality + Primary Goal Changes?",
            "score": 120,
            "num_comments": 18,
            "created_at": "2026-04-05T00:00:00Z",
            "collected_at": "2026-04-05T00:00:00Z",
            "collect_batch_id": "batch-paid-1",
            "time_window": "7d",
            "signal_level": "sustained",
            "why_now_reason": "switch_signal_7d",
            "listing_source": "search",
            "primary_reason": "paid-economics:problem_keyword",
            "matched_keywords": ["blended cac"],
            "top_communities": ["r/PPC"],
            "thread_count": 1,
            "community_count": 1,
            "quote_count": 2,
            "intent_tags": ["替换", "求推荐"],
            "evidence_quotes": [
                {
                    "text": "A ROAS drop from 7x to 2x after switching offline conversions to primary is a specific signal.",
                    "community": "r/PPC",
                    "permalink": "https://www.reddit.com/r/PPC/comments/ppc123/q1",
                },
                {
                    "text": "The volume of 21 imported conversions is too thin for the model to trust.",
                    "community": "r/PPC",
                    "permalink": "https://www.reddit.com/r/PPC/comments/ppc123/q2",
                },
            ],
        }
    )


def _business_growth_candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            **_candidate().model_dump(mode="json"),
            "candidate_id": "cand-bgo-001",
            "signal_id": "sig-bgo-001",
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "funnel-conversion",
            "matched_subreddit": "marketing",
            "title": "Reddit ads are the WORST marketing spend I’ve ever had",
            "matched_keywords": ["click fraud"],
            "top_communities": ["r/marketing"],
            "intent_tags": ["求推荐"],
            "evidence_quotes": [
                {
                    "text": "Reddit ads feel like the worst spend I've had this year.",
                    "community": "r/marketing",
                    "permalink": "https://www.reddit.com/r/marketing/comments/1sbspma/q1",
                },
                {
                    "text": "I’m starting to question whether this budget should stay on Reddit at all.",
                    "community": "r/marketing",
                    "permalink": "https://www.reddit.com/r/marketing/comments/1sbspma/q2",
                },
            ],
        }
    )


def _agent_builder_candidate() -> CandidatePack:
    return CandidatePack.model_validate(
        {
            **_candidate().model_dump(mode="json"),
            "candidate_id": "cand-agent-builder-001",
            "signal_id": "sig-agent-builder-001",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "agent-builder",
            "matched_subreddit": "automation",
            "title": "The bull** around AI agent capabilities on Reddit is getting out of hand",
            "matched_keywords": ["context loss in agent loop"],
            "top_communities": ["r/automation"],
            "intent_tags": ["替换"],
            "evidence_quotes": [
                {
                    "text": "It’s only through A LOT of prompt engineering and for very specific use cases.",
                    "community": "r/automation",
                    "permalink": "https://www.reddit.com/r/automation/comments/1saabgz/q1",
                },
                {
                    "text": "Sometimes it's better to do the work myself or through a cron job. The costs can be significant.",
                    "community": "r/automation",
                    "permalink": "https://www.reddit.com/r/automation/comments/1saabgz/q2",
                },
            ],
        }
    )


def test_polish_generated_text_cleans_summary_restatement_prefix() -> None:
    result = polish_generated_text(
        "几条讨论都在说同一件事：工具一多以后，上下文总在来回搬，最后没人愿意坚持那套流程。",
        field_name="summary_line",
    )
    assert result == "工具一多以后，上下文总在来回搬，最后没人愿意坚持那套流程。"


def test_polish_generated_text_makes_title_more_colloquial() -> None:
    result = polish_generated_text(
        "ROAS从7x暴跌至2x，切换offline转化primary后算法重学仅21数据",
        field_name="title",
    )
    assert result == "ROAS 从 7x 掉到 2x，把线下成交改成主要优化目标后，算法只拿到 21 条数据"


def test_polish_generated_text_softens_reporty_title_phrasing() -> None:
    result = polish_generated_text(
        "做 AI 代码工具的人，开始被要求先拿具体错误清单，不再靠标题党。",
        field_name="title",
    )
    assert result == "做 AI 代码工具的人，得先拿出具体错误清单，不能再靠标题党"


def test_semantic_rewrite_smooths_abrupt_title_bridge() -> None:
    rules = load_card_content_rules()
    rewrite_phrases = (rules.get("semantic_readout") or {}).get("rewrite_phrases") or {}
    title = "Meta 广告投手集体抱怨：不是今天崩了，是过去一个月都在烂"
    for source, target in rewrite_phrases.items():
        title = title.replace(str(source), str(target))

    assert "今天崩了" not in title
    assert "都在烂" not in title
    assert "单日波动" in title
    assert "没跑顺" in title


def test_semantic_readout_does_not_append_junk_terms_to_natural_continue_signal() -> (
    None
):
    rules = load_card_content_rules()
    source = seed_validation_draft(_agent_builder_candidate())
    draft = source.model_copy(
        update={
            "detail": source.detail.model_copy(
                update={
                    "continue_signal": "观察更多关于 AI 处理多文件上下文限制的讨论，以及开发者是否转向更专业的 Agent 模式。",
                    "why_test_now": "关键证据是“10 files and external database”。这说明讨论已经进入复杂工程上下文。",
                }
            )
        }
    )

    result = finalize_signal_readout(draft, source_draft=source, rules=rules)

    assert "继续看 The native" not in result.detail.continue_signal
    assert (
        result.detail.continue_signal
        == "观察更多关于 AI 处理多文件上下文限制的讨论，以及开发者是否转向更专业的 Agent 模式。"
    )
    assert result.detail.why_test_now.startswith("关键证据是")


def test_semantic_readout_keeps_rewrite_phrases_as_small_safety_net() -> None:
    rules = load_card_content_rules()
    rewrite_phrases = (rules.get("semantic_readout") or {}).get("rewrite_phrases") or {}

    assert len(rewrite_phrases) <= 30
    assert "不是今天崩了，是过去一个月都在烂" in rewrite_phrases
    assert "系统性失灵" not in rewrite_phrases
    assert "情绪发泄" not in rewrite_phrases


def test_validated_text_applies_rewrite_phrases_before_banned_check() -> None:
    rules = load_card_content_rules()

    text = _validated_text("这说明判断依据已经从 A 转移到了 B", "why_now", rules)

    assert text == "判断重点从 A 转向 B"


def test_validated_text_rewrites_vague_title_hook_before_banned_check() -> None:
    rules = load_card_content_rules()

    text = _validated_text("写了800行提示词，评论区却在问：这到底是什么？", "title", rules)
    pronoun_text = _validated_text("Reddit 评论区追问它到底解决了什么问题", "title", rules)

    assert text == "写了800行提示词，评论区却在问：具体用途是什么？"
    assert pronoun_text == "Reddit 评论区追问这个方案解决了什么问题"


def test_validated_text_spaces_english_abbreviations_in_title() -> None:
    rules = load_card_content_rules()

    text = _validated_text("老SEO说别追GEO了，AI味内容的ROI正在下降", "title", rules)

    assert text == "老 SEO 说别追 GEO 了，AI 味内容的 ROI 正在下降"


def test_polish_generated_text_rewrites_detail_banned_report_phrases() -> None:
    text = polish_generated_text(
        "这句话把讨论重心直接点出了，后面如果继续翻车，下一步再看。",
        field_name="detail",
    )

    assert text == "这句话让讨论焦点指出了，后面如果继续出问题，后续动作再看。"


def test_semantic_prompt_extra_is_only_light_pack_guidance() -> None:
    rules = load_card_content_rules()
    prompt = semantic_prompt_extra(
        rules=rules, lane="signal", topic_pack_id="paid-economics"
    )

    assert "避开报告腔抽象词" not in prompt
    assert "避开用力过猛的情绪词" not in prompt
    assert "不要逐词改写" not in prompt
    assert "这是投放经济信号" in prompt


def test_v13_semantic_brief_schema_gives_writer_reasoning_actionable_fields() -> None:
    schema = _semantic_brief_json_schema()
    required = set(schema["required"])

    assert {
        "core_scene",
        "actor_and_scene",
        "supported_claim",
        "evidence_basis",
        "lane_specific",
        "tension_or_decision",
        "why_now_readout",
        "risk_bounds",
        "writing_focus",
        "avoid_claims",
        "uncertainty",
    }.issubset(required)
    assert schema["properties"]["evidence_basis"]["type"] == "ARRAY"
    evidence_item = schema["properties"]["evidence_basis"]["items"]
    assert evidence_item["type"] == "OBJECT"
    assert {"claim", "community", "quote_text", "permalink"}.issubset(
        set(evidence_item["required"])
    )
    lane_specific = schema["properties"]["lane_specific"]["properties"]
    assert {"hot", "signal", "breakdown"}.issubset(set(lane_specific))
    assert "controversy_axis" in lane_specific["hot"]["properties"]
    assert "buying_or_adoption_signal" in lane_specific["signal"]["properties"]
    assert "synthesis_angle" in lane_specific["breakdown"]["properties"]
    uncertainty = schema["properties"]["uncertainty"]["properties"]
    assert {
        "confidence",
        "missing_evidence",
        "weak_points",
        "single_thread_risk",
    }.issubset(set(uncertainty))
    assert schema["properties"]["avoid_claims"]["items"]["type"] == "STRING"


def test_v13_semantic_brief_input_keeps_evidence_short_and_bounded() -> None:
    long_quote = "A" * 600
    candidate = _candidate(
        thread_count=6,
        community_count=3,
        quotes=[
            {
                "text": f"{long_quote}-{index}",
                "community": f"r/source{index}",
                "permalink": f"https://www.reddit.com/r/source/comments/post/q{index}",
            }
            for index in range(6)
        ],
    )
    draft = seed_validation_draft(candidate)

    payload = _semantic_brief_input(draft)

    assert len(payload["evidence_quotes"]) == 3
    assert all(len(item["text"]) <= 260 for item in payload["evidence_quotes"])


@pytest.mark.asyncio
async def test_v13_semantic_brief_uses_dedicated_output_budget() -> None:
    seen: dict[str, int] = {}

    class SemanticClient:
        async def generate(self, *_args, **kwargs) -> str:
            seen["max_tokens"] = int(kwargs["max_tokens"])
            return json.dumps(
                {
                    "core_scene": "场景",
                    "actor_and_scene": "主体和场景",
                    "supported_claim": "可证明判断",
                    "evidence_basis": [],
                    "lane_specific": {
                        "hot": {
                            "flashpoint": "焦点",
                            "debate_sides": "双方",
                            "controversy_axis": "争议轴",
                            "why_people_argue": "原因",
                        },
                        "signal": {
                            "target_user": "用户",
                            "pain_trigger": "痛点",
                            "buying_or_adoption_signal": "信号",
                            "testability": "验证",
                        },
                        "breakdown": {
                            "repeated_pattern": "模式",
                            "cross_thread_commonality": "共性",
                            "thesis_candidate": "论点",
                            "synthesis_angle": "角度",
                        },
                    },
                    "tension_or_decision": "张力",
                    "why_now_readout": "时间判断",
                    "risk_bounds": "边界",
                    "writing_focus": "写作重点",
                    "avoid_claims": [],
                    "uncertainty": {
                        "confidence": "medium",
                        "missing_evidence": [],
                        "weak_points": [],
                        "single_thread_risk": "低",
                    },
                },
                ensure_ascii=False,
            )

    await _generate_profile_semantic_brief(
        seed_validation_draft(_candidate()),
        model="google/gemini-3-flash-preview",
        client_factory=lambda _model, _timeout: SemanticClient(),
    )

    assert seen["max_tokens"] >= 2600


@pytest.mark.asyncio
async def test_generate_json_logs_invalid_payload_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class BadJsonClient:
        async def generate(self, *_args, **_kwargs) -> str:
            return '{"title":"bad'

    target_logger = logging.getLogger("app.services.hotpost.card_content_generator")
    target_logger.disabled = False
    target_logger.propagate = True
    caplog.set_level(logging.WARNING, logger=target_logger.name)

    with pytest.raises(ValueError, match="LLM returned invalid JSON"):
        await _generate_json(
            model="google/gemini-3-flash-preview",
            timeout=1.0,
            messages=[{"role": "user", "content": "hello"}],
            client_factory=lambda _model, _timeout: BadJsonClient(),
            max_tokens=16,
            trace_id="draft-cand-test",
            stage="semantic_brief",
        )

    assert "stage=semantic_brief" in caplog.text
    assert "model=google/gemini-3-flash-preview" in caplog.text
    assert "trace_id=draft-cand-test" in caplog.text
    assert "raw_head=" in caplog.text
    assert "raw_tail=" in caplog.text


def test_finalize_signal_readout_only_uses_small_safety_net_rewrites() -> None:
    rules = load_card_content_rules()
    source = seed_validation_draft(_paid_econ_candidate())
    draft = source.model_copy(
        update={
            "title": "Meta 投手集体抱怨：不是今天崩了，是过去一个月都在烂",
            "summary_line": "大家不再纠结单日数据异常，而是确认过去一个月出现了持续性的效果崩塌。",
            "why_now": "这不再是偶尔的系统波动，而是投手们正在重新评估 Meta 算法的稳定性。",
            "detail": source.detail.model_copy(
                update={
                    "why_test_now": "从“单日吐槽”到“月度复盘”的视角转换。",
                    "continue_signal": "继续看 delivery down 这些词是否频繁出现。",
                    "stop_signal": "如果后续讨论回到素材和受众设置，就不用放大。",
                }
            ),
        }
    )

    result = finalize_signal_readout(draft, source_draft=source, rules=rules)

    assert "今天崩了" not in result.title
    assert "都在烂" not in result.title
    assert "单日波动" in result.title
    assert "没跑顺" in result.title
    assert "频繁出现" not in result.detail.continue_signal
    assert "会不会继续出现" in result.detail.continue_signal


def test_finalize_signal_readout_adds_evidence_anchor_when_fields_are_too_generic() -> (
    None
):
    rules = load_card_content_rules()
    source = seed_validation_draft(
        _candidate(
            title="Cursor Composer 2 Fast bigger model cost reduction",
            topic_pack_id="agent-builder",
            matched_subreddit="cursor",
            top_communities=["r/cursor"],
            quotes=[
                {
                    "text": "I would rather use a bigger model in that case, even if it is slower.",
                    "community": "r/cursor",
                    "permalink": "https://www.reddit.com/r/cursor/comments/a/q1",
                },
                {
                    "text": "The faster tier only makes sense if the cost reduction is actually meaningful.",
                    "community": "r/cursor",
                    "permalink": "https://www.reddit.com/r/cursor/comments/a/q2",
                },
            ],
        )
    )
    draft = source.model_copy(
        update={
            "why_now": "用户开始重新判断快模型到底值不值。",
            "detail": source.detail.model_copy(
                update={
                    "why_test_now": "用户已经开始质疑这个功能是不是鸡肋。",
                    "continue_signal": "如果后面有用户晒出具体对比测试，这条线就值得继续看。",
                    "stop_signal": "如果讨论只剩个人偏好，就不用放大。",
                }
            ),
        }
    )

    result = finalize_signal_readout(draft, source_draft=source, rules=rules)

    assert "原话里" in result.detail.why_test_now
    assert "bigger model" in result.detail.why_test_now
    assert "继续看" in result.detail.continue_signal
    assert "具体对比测试" in result.detail.continue_signal


def test_finalize_signal_readout_skips_auto_summary_quote_when_anchoring() -> None:
    rules = load_card_content_rules()
    source = seed_validation_draft(
        _candidate(
            title="Anthropic stop shipping complaint",
            topic_pack_id="agent-builder",
            matched_subreddit="ClaudeAI",
            top_communities=["r/ClaudeAI"],
            quotes=[
                {
                    "text": "**TL;DR of the discussion generated automatically after 200 comments.** The community agrees quality is down.",
                    "community": "r/ClaudeAI",
                    "permalink": "https://www.reddit.com/r/ClaudeAI/comments/a/q1",
                },
                {
                    "text": "Cancel your subs. Write exactly why. Nothing sends feedback like cancelling a 200 dollar sub.",
                    "community": "r/ClaudeAI",
                    "permalink": "https://www.reddit.com/r/ClaudeAI/comments/a/q2",
                },
            ],
        )
    )
    draft = source.model_copy(
        update={
            "why_now": "讨论已经从吐槽走到真有人开始退订。",
            "detail": source.detail.model_copy(
                update={
                    "why_test_now": "大家已经不只是骂，而是在晒动作。",
                    "continue_signal": "如果后面继续有人晒退订和账单，就继续看。",
                    "stop_signal": "如果只剩情绪复读，就不用放大。",
                }
            ),
        }
    )

    result = finalize_signal_readout(draft, source_draft=source, rules=rules)

    assert "TL;DR of the discussion" not in result.detail.why_test_now
    assert "cancelling a 200 dollar sub" in result.detail.why_test_now


def test_generate_card_content_hot_anchoring_uses_neutral_template_without_ellipsis() -> (
    None
):
    rules = load_card_content_rules()
    source = seed_validation_draft(
        _candidate(
            title="Anthropic stop shipping complaint",
            score=320,
            num_comments=120,
            signal_level="hot",
            why_now_reason="new_threads_24h",
            listing_source="listing:hot:day",
            matched_subreddit="ClaudeAI",
            top_communities=["r/ClaudeAI"],
            quotes=[
                {
                    "text": "I cancelled my 200 sub. I HOPE to re-sub. But honestly Cancelling it is the ONLY way to make them listen and get a response from Anthropic.",
                    "community": "r/ClaudeAI",
                    "permalink": "https://www.reddit.com/r/ClaudeAI/comments/a/q1",
                },
                {
                    "text": "Some people think the feature team and model team are separate, but most replies say paying users are being used as testers.",
                    "community": "r/ClaudeAI",
                    "permalink": "https://www.reddit.com/r/ClaudeAI/comments/a/q2",
                },
            ],
        )
    )
    draft = source.model_copy(
        update={
            "lane": "hot",
            "why_now": "讨论已经从吐槽走到真有人开始退订。",
            "detail": source.detail.model_copy(
                update={
                    "why_test_now": "大家已经从抱怨走到晒动作了。",
                    "continue_signal": "继续看更多退订和账单截图。",
                    "stop_signal": "如果只剩情绪复读，就不用放大。",
                }
            ),
        }
    )

    result = finalize_signal_readout(draft, source_draft=source, rules=rules)

    assert result.detail.why_test_now.startswith("关键证据是“")
    assert "原话里有个关键句" not in result.detail.why_test_now
    assert "..." not in result.detail.why_test_now


def test_finalize_hot_readout_rewrites_translationese_and_strips_ellipsis() -> None:
    rules = load_card_content_rules()
    source = seed_validation_draft(
        _candidate(
            title="Anthropic token rumor fight",
            score=280,
            num_comments=96,
            signal_level="hot",
            why_now_reason="new_threads_24h",
            listing_source="listing:hot:day",
            matched_subreddit="ClaudeAI",
            top_communities=["r/ClaudeAI"],
            quotes=[
                {
                    "text": "The post makes it sound like a hidden optimization... that's misleading.",
                    "community": "r/ClaudeAI",
                    "permalink": "https://www.reddit.com/r/ClaudeAI/comments/a/q1",
                },
                {
                    "text": "This is just marketing for his plugin.",
                    "community": "r/ClaudeAI",
                    "permalink": "https://www.reddit.com/r/ClaudeAI/comments/a/q2",
                },
            ],
        )
    )
    draft = source.model_copy(
        update={
            "lane": "hot",
            "summary_line": "争议焦点在于：到底是 Anthropic 故意让你多花钱，还是发帖人在利用“Token 焦虑”造谣推销插件。关键原话是：The post makes it sound like a hidden optimization... that's misleading.。",
            "why_now": "这帖火是因为技术讨论已经变成了对发帖人动机的怀疑。",
            "detail": HotValidationDetail.model_validate(
                {
                    "flashpoint": "一条讲省钱技巧的帖，越聊越像在卖插件。",
                    "fight_line": "是 Anthropic 真在偷偷多收钱，还是发帖人在借焦虑带货。",
                    "why_test_now": "原话里提到 marketing for his plugin。大家发现所谓的省钱大招其实是带货软文，这种反转让讨论从技术交流变成了信誉审判。",
                    "continue_signal": "继续看更多人开始扒发帖人动机。",
                    "stop_signal": "如果后面只剩重复骂战，就先别放大。",
                }
            ),
        }
    )

    result = finalize_validation_readout(draft, source_draft=source, rules=rules)
    hot_detail = result.detail

    assert "..." not in result.summary_line
    assert "原话里" not in hot_detail.why_test_now
    assert hot_detail.why_test_now.startswith("关键证据是“marketing for his plugin”")


def test_finalize_signal_readout_does_not_append_duplicate_terms_when_continue_signal_is_specific() -> (
    None
):
    rules = load_card_content_rules()
    source = seed_validation_draft(
        _candidate(
            title="Cursor Composer Fast pricing cost reduction",
            topic_pack_id="agent-builder",
            matched_subreddit="cursor",
            top_communities=["r/cursor"],
            quotes=[
                {
                    "text": "I'd prefer the option of an even slower one for more cost reduction.",
                    "community": "r/cursor",
                    "permalink": "https://www.reddit.com/r/cursor/comments/a/q1",
                },
                {
                    "text": "Composer Fast pricing only makes sense if the cheaper tier is meaningful.",
                    "community": "r/cursor",
                    "permalink": "https://www.reddit.com/r/cursor/comments/a/q2",
                },
            ],
        )
    )
    draft = source.model_copy(
        update={
            "detail": source.detail.model_copy(
                update={
                    "why_test_now": "原话里已经把取舍说清楚。",
                    "continue_signal": "继续看『cost reduction』、『cheaper model』或者『API usage limit』这些词。",
                    "stop_signal": "如果后续只剩个人偏好，就不用放大。",
                }
            ),
        }
    )

    result = finalize_signal_readout(draft, source_draft=source, rules=rules)

    assert result.detail.continue_signal.count("继续看") == 1
    assert "doesn" not in result.detail.continue_signal


def test_polish_generated_text_rewrites_backend_jargon_for_client_copy() -> None:
    result = polish_generated_text(
        "把 offline 转化切到 primary 后，导入转化数据太薄，模型不信任。",
        field_name="summary_line",
    )
    assert result == "把线下成交改成主要优化目标后，样本太少，系统一下学不稳。"


def test_polish_generated_text_rewrites_ai_jargon_for_client_copy() -> None:
    result = polish_generated_text(
        "multi-step agent pipelines 最怕 silent failure，workflow 看着正常其实已经跑偏。",
        field_name="summary_line",
    )
    assert "悄悄跑偏" in result
    assert "流程" in result


def test_polish_generated_text_keeps_slash_commands_readable() -> None:
    result = polish_generated_text(
        "Claude Code 上线 /workflows，开发者预判自建工具将被替代。",
        field_name="title",
    )
    assert "/workflows" in result
    assert "/流程" not in result


def test_polish_generated_text_rewrites_growth_blackwords_for_client_copy() -> None:
    result = polish_generated_text(
        "Reddit 广告先被人判成 click fraud 重灾区，checkout 也撑不住。",
        field_name="title",
    )
    assert "click fraud" not in result.lower()
    assert "无效点击" in result
    assert "结账页" in result


def test_polish_generated_text_rewrites_client_pronoun_and_brain_words() -> None:
    result = polish_generated_text(
        "人一边靠 AI 省脑子，一边也开始怕自己越来越不判断了。",
        field_name="title",
    )
    assert "人一边" not in result
    assert "脑子" not in result
    assert "用户一边" in result
    assert "思考" in result


def test_polish_generated_text_rewrites_growth_jargon_and_generic_human_words() -> None:
    result = polish_generated_text(
        "拥挤SEO工具市场缺少chess niche的社区信任捷径和伙伴分销零CAC，用户见过太多AI平台惯世媚俗爱G2比价。",
        field_name="detail",
    )
    assert "niche" not in result
    assert "CAC" not in result
    assert "G2" not in result
    assert "SEO" in result
    assert "细分类目" in result
    assert "获客成本" in result
    assert "比价站" in result


def test_load_card_content_models_prefers_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTPOST_REASONING_MODEL", "z-ai/glm-5.1")
    monkeypatch.setenv("HOTPOST_REASONING_ENABLED", "true")
    load_card_content_models.cache_clear()
    try:
        models = load_card_content_models()
    finally:
        load_card_content_models.cache_clear()
    assert models["reasoning_model"] == "z-ai/glm-5.1"
    assert models["reasoning_enabled"] is True


def test_load_card_content_models_reads_hot_lane_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_FAST_MODEL", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_MODEL", raising=False)
    load_card_content_models.cache_clear()
    try:
        models = load_card_content_models()
    finally:
        load_card_content_models.cache_clear()
    assert models["fast_model"] == "deepseek/deepseek-v4-flash"
    assert models["reasoning_model"] == "deepseek/deepseek-v4-pro"
    assert models["fast_model_pack_overrides"] == {}
    assert models["fast_model_lane_overrides"] == {
        "hot": {"model": "google/gemini-3-flash-preview", "timeout_seconds": 22.0}
    }


def test_load_card_content_models_exposes_hotpost_v12_route_profile_without_enabling_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_FAST_MODEL", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_MODEL", raising=False)
    load_card_content_models.cache_clear()
    try:
        models = load_card_content_models()
    finally:
        load_card_content_models.cache_clear()

    profile = models["route_profiles"]["hotpost_v12"]

    assert models["fast_model"] == "deepseek/deepseek-v4-flash"
    assert models["reasoning_model"] == "deepseek/deepseek-v4-pro"
    assert profile["semantic_model"] == "deepseek/deepseek-v4-flash"
    assert profile["writer_model"] == "deepseek/deepseek-v4-pro"
    assert profile["enabled_by_default"] is False


def test_load_card_content_models_exposes_hotpost_v13_title_route_profile_without_enabling_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_FAST_MODEL", raising=False)
    monkeypatch.delenv("HOTPOST_REASONING_MODEL", raising=False)
    load_card_content_models.cache_clear()
    try:
        models = load_card_content_models()
    finally:
        load_card_content_models.cache_clear()

    profile = models["route_profiles"]["hotpost_v13_title_standalone"]

    assert models["fast_model"] == "deepseek/deepseek-v4-flash"
    assert models["reasoning_model"] == "deepseek/deepseek-v4-pro"
    assert profile["semantic_model"] == "google/gemini-3-flash-preview"
    assert profile["writer_model"] == "deepseek/deepseek-v4-pro"
    assert profile["enabled_by_default"] is False


def test_load_card_content_models_reads_v13_production_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_CARD_CONTENT_PROFILE_ID", raising=False)
    load_card_content_models.cache_clear()
    try:
        models = load_card_content_models()
    finally:
        load_card_content_models.cache_clear()

    assert models["production_profile_id"] == "hotpost_v13_title_standalone"


def test_generation_field_contract_no_longer_owns_copywriting_prompt() -> None:
    load_card_content_rules.cache_clear()
    try:
        prompt = build_generation_field_contract_prompt(load_card_content_rules())
    finally:
        load_card_content_rules.cache_clear()

    assert prompt == ""


def test_signal_prompt_budget_keeps_role_readable() -> None:
    rules = load_card_content_rules()
    draft = seed_validation_draft(_paid_econ_candidate())
    messages = build_signal_prompt(
        draft,
        banned_patterns=all_banned_patterns(rules),
        field_contract_prompt=build_generation_field_contract_prompt(rules),
    )
    system = messages[0]["content"] + semantic_prompt_extra(
        rules=rules,
        lane="signal",
        topic_pack_id=draft.topic_pack_id,
    )

    assert len(system) <= 3600
    assert system.count("不要") <= 18
    assert system.count("why_now") <= 5
    assert system.count("why_test_now") <= 5
    assert "R站资深专家" in system
    assert "只用输入证据，不补背景" in system
    assert "这张卡只回答一件事：谁开始把原来的判断顺序换掉了" in system
    assert "Reddit 是全球最大的未美化需求数据库" not in system


def test_signal_prompt_does_not_ask_llm_to_generate_min_test_action() -> None:
    rules = load_card_content_rules()
    draft = seed_validation_draft(_candidate())
    messages = build_signal_prompt(
        draft,
        banned_patterns=all_banned_patterns(rules),
        field_contract_prompt=build_generation_field_contract_prompt(rules),
    )
    user_payload = json.loads(messages[1]["content"])

    assert "detail.min_test_action" not in messages[0]["content"]
    assert "min_test_action" not in user_payload["output_schema"]["detail"]


def test_signal_prompt_payload_only_keeps_generation_inputs() -> None:
    rules = load_card_content_rules()
    draft = seed_validation_draft(_paid_econ_candidate())
    messages = build_signal_prompt(
        draft,
        banned_patterns=all_banned_patterns(rules),
        field_contract_prompt=build_generation_field_contract_prompt(rules),
    )
    user_payload = json.loads(messages[1]["content"])

    assert "source_scope_id" not in user_payload
    assert "source_scope_name" not in user_payload
    assert "source_communities" not in user_payload
    assert "matched_subreddit" not in user_payload
    assert "quote_count" not in user_payload
    assert "source_link" not in user_payload
    assert "card_type_requested" not in user_payload
    assert user_payload["topic_pack_id"] == "paid-economics"
    assert user_payload["stats"] == {
        "thread_count": 1,
        "community_count": 1,
        "signal_level": "sustained",
        "why_now_reason": "switch_signal_7d",
        "intent_tags": ["替换", "求推荐"],
    }
    assert "\n" not in messages[1]["content"]


class _FakeClient:
    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = payloads

    async def generate(self, *_args, **_kwargs) -> str:
        if not self._payloads:
            raise AssertionError("unexpected LLM call")
        return json.dumps(self._payloads.pop(0), ensure_ascii=False)


class _RecordingClient(_FakeClient):
    def __init__(self, payloads: list[dict]) -> None:
        super().__init__(payloads)
        self.messages = None

    async def generate(self, prompt, **kwargs) -> str:
        self.messages = prompt
        return await super().generate(prompt, **kwargs)


def _precheck_payload() -> dict:
    return {
        "decision": "PASS",
        "reasons": ["证据支撑当前主张"],
        "required_fixes": [],
        "risk_flags": [],
        "publish_note": "可以进入人工 review",
    }


class _RawClient:
    def __init__(self, raw: str) -> None:
        self.raw = raw

    async def generate(self, *_args, **_kwargs) -> str:
        return self.raw


class _RawSequenceClient:
    def __init__(self, raws: list[str]) -> None:
        self.raws = raws
        self.calls: list[dict] = []

    async def generate(self, *_args, **kwargs) -> str:
        self.calls.append(kwargs)
        if not self.raws:
            raise AssertionError("unexpected LLM call")
        return self.raws.pop(0)


class _RecordingRawClient(_RawClient):
    def __init__(self, raw: str) -> None:
        super().__init__(raw)
        self.response_format = None

    async def generate(self, *_args, **kwargs) -> str:
        self.response_format = kwargs.get("response_format")
        return self.raw


@pytest.mark.asyncio
async def test_generate_json_accepts_single_object_array_for_gemini_flash() -> None:
    payload = await _generate_json(
        model="google/gemini-3-flash-preview",
        timeout=60,
        messages=[],
        client_factory=lambda _model, _timeout: _RawClient('[{"title": "ok"}]'),
    )

    assert payload == {"title": "ok"}


@pytest.mark.asyncio
async def test_generate_json_normalizes_control_chars_inside_strings() -> None:
    payload = await _generate_json(
        model="google/gemini-3-flash-preview",
        timeout=60,
        messages=[],
        client_factory=lambda _model, _timeout: _RawClient(
            '{"title": "ok", "summary_line": "第一行\n第二行"}'
        ),
    )

    assert payload == {"title": "ok", "summary_line": "第一行\n第二行"}


@pytest.mark.asyncio
async def test_generate_json_extracts_object_when_response_has_extra_text() -> None:
    payload = await _generate_json(
        model="deepseek/deepseek-v4-pro",
        timeout=60,
        messages=[{"role": "system", "content": "return json"}],
        client_factory=lambda _model, _timeout: _RawClient(
            'note before {"title":"ok","summary_line":"可解析"} trailing note'
        ),
    )

    assert payload == {"title": "ok", "summary_line": "可解析"}


@pytest.mark.asyncio
async def test_generate_json_classifies_empty_response_without_repair() -> None:
    client = _RawSequenceClient([""])

    with pytest.raises(ValueError, match="empty_response"):
        await _generate_json(
            model="deepseek/deepseek-v4-pro",
            timeout=60,
            messages=[{"role": "system", "content": "return json"}],
            client_factory=lambda _model, _timeout: client,
        )

    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_generate_json_retries_once_when_gemini_returns_broken_json() -> None:
    client = _RawSequenceClient(
        [
            '{"title":"没闭合"',
            '{"title":"ok","summary_line":"已修复"}',
        ]
    )

    payload = await _generate_json(
        model="google/gemini-3-flash-preview",
        timeout=60,
        messages=[{"role": "system", "content": "return json"}],
        client_factory=lambda _model, _timeout: client,
    )

    assert payload == {"title": "ok", "summary_line": "已修复"}
    assert len(client.calls) == 2
    assert client.calls[1]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_generate_json_retries_twice_for_gemini_when_second_attempt_is_still_broken() -> None:
    client = _RawSequenceClient(
        [
            '{"title":"第一次没闭合"',
            '{"title":"第二次还是没闭合"',
            '{"title":"ok","summary_line":"第三次修复"}',
        ]
    )

    payload = await _generate_json(
        model="google/gemini-3-flash-preview",
        timeout=60,
        messages=[{"role": "system", "content": "return json"}],
        client_factory=lambda _model, _timeout: client,
    )

    assert payload == {"title": "ok", "summary_line": "第三次修复"}
    assert len(client.calls) == 3
    assert client.calls[1]["temperature"] == 0.0
    assert client.calls[2]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_generate_json_uses_repair_pass_for_non_google_models_after_broken_retries() -> None:
    client = _RawSequenceClient(
        [
            '{"title":"第一次没闭合"',
            '{"title":"第二次还是没闭合"',
            '{"title":"ok","summary_line":"修复通道已接住"}',
        ]
    )

    payload = await _generate_json(
        model="deepseek/deepseek-v4-pro",
        timeout=60,
        messages=[{"role": "system", "content": "return json"}],
        client_factory=lambda _model, _timeout: client,
    )

    assert payload == {"title": "ok", "summary_line": "修复通道已接住"}
    assert len(client.calls) == 3
    assert client.calls[1]["temperature"] == 0.0
    assert client.calls[2]["temperature"] == 0.0
    assert client.calls[2]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_generate_json_adds_schema_only_for_gemini_models() -> None:
    gemini_client = _RecordingRawClient('{"title": "ok"}')
    other_client = _RecordingRawClient('{"title": "ok"}')
    schema = _card_content_json_schema_for_draft(seed_validation_draft(_candidate()))

    await _generate_json(
        model="google/gemini-3-flash-preview",
        timeout=60,
        messages=[],
        client_factory=lambda _model, _timeout: gemini_client,
        response_schema=schema,
    )
    await _generate_json(
        model="deepseek/deepseek-v4-pro",
        timeout=60,
        messages=[],
        client_factory=lambda _model, _timeout: other_client,
        response_schema=schema,
    )

    assert gemini_client.response_format["type"] == "json_object"
    assert gemini_client.response_format["schema"]["type"] == "OBJECT"
    assert "detail" in gemini_client.response_format["schema"]["required"]
    assert other_client.response_format == {"type": "json_object"}


@pytest.mark.asyncio
async def test_generate_json_rejects_multi_object_array() -> None:
    with pytest.raises(ValueError, match="LLM payload must be a JSON object"):
        await _generate_json(
            model="google/gemini-3-flash-preview",
            timeout=60,
            messages=[],
            client_factory=lambda _model, _timeout: _RawClient(
                '[{"title": "one"}, {"title": "two"}]'
            ),
        )


@pytest.mark.asyncio
async def test_generate_card_content_returns_signal_card_and_reorders_preview_quote() -> None:
    draft = seed_validation_draft(_candidate())
    payloads = [
        {
            "title": "销售团队在吵：每天都在给 CRM 补作业",
            "summary_line": "r/sales 有人说“我每天要花 30 分钟喂 Salesforce 数据”。同一周里，不止一个帖子在讲类似负担。",
            "audience": "5-50 人团队里每天要回填 CRM 的一线销售",
            "why_now": "本周 r/sales 至少 1 帖在讲这件事，讨论已经带出替代意图，已经有人开始问替代方案。",
            "preview_quote_permalink": "https://www.reddit.com/r/startups/comments/def456/q2",
            "detail": {
                "pain_point": "原话里反复出现的是：销售觉得自己在替系统补行政作业。",
                "target_user_and_scene": "一线销售每天要在成交之外补 CRM 字段的场景。",
                "why_test_now": "这轮讨论已经从吐槽走到找替代方案。",
                "continue_signal": "如果后续继续出现“替代”“轻量”“不想回填”这些词，值得继续盯。",
                "stop_signal": "如果后续只剩单帖情绪、没有人继续补充具体场景，可以先放过。",
            },
        }
    ]
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
    )
    assert result.card_type == "validate"
    assert result.detail.min_test_action == "去看原始讨论"
    assert (
        result.evidence_quotes[0].permalink
        == "https://www.reddit.com/r/startups/comments/def456/q2"
    )
    assert result.title == "销售团队在吵：每天都在给 CRM 补作业"


@pytest.mark.asyncio
async def test_generate_card_content_uses_v13_production_profile_before_hot_lane_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_CARD_CONTENT_PROFILE_ID", raising=False)
    load_card_content_models.cache_clear()
    seeded = seed_validation_draft(
        _candidate(
            topic_pack_id="agent-builder",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
        )
    )
    draft = seeded.model_copy(
        update={"lane": "hot", "detail": empty_validation_detail_payload("hot")}
    )
    payloads = [
        {
            "core_scene": "评论区围绕销售团队是否被 CRM 行政工作拖住分裂。",
            "supported_claim": "证据只支持一小批销售开始怀疑 CRM 回填负担。",
            "risk_bounds": "不能放大成所有销售团队都在迁移。",
        },
        {
            "title": "销售团队质疑 CRM 回填是在替系统补作业",
            "summary_line": "r/sales 里有人把 Salesforce 回填说成每天 30 分钟的额外行政负担。",
            "audience": "每天要补 CRM 字段的一线销售和小团队负责人",
            "why_now": "本周讨论已经从吐槽回填负担，走到有人评估更轻的替代方案。",
            "preview_quote_permalink": "https://www.reddit.com/r/startups/comments/def456/q2",
            "detail": {
                "flashpoint": "争议点是 CRM 到底帮销售推进成交，还是把销售变成数据录入员。",
                "fight_line": "支持派觉得数据完整才方便管理，反对派觉得一线销售被行政动作拖慢。",
                "why_test_now": "已有评论直接提到每天 30 分钟回填和评估轻量替代。",
                "continue_signal": "继续看 CRM updates、lighter alternatives 这些词是不是继续出现。",
                "stop_signal": "如果后续只剩单帖吐槽，没有替代方案讨论，可以先放过。",
            },
        },
        _precheck_payload(),
    ]
    seen_models: list[str] = []

    def factory(model: str, timeout: float) -> _FakeClient:
        seen_models.append(model)
        return _FakeClient(payloads)

    result = await generate_card_content(
        draft, client_factory=factory, allow_breakdown=False
    )

    assert seen_models[:2] == [
        "google/gemini-3-flash-preview",
        "deepseek/deepseek-v4-pro",
    ]
    assert "xiaomi/mimo-v2.5-pro" not in seen_models
    assert result.lane == "hot"
    assert result.title == "销售团队质疑 CRM 回填是在替系统补作业"


@pytest.mark.asyncio
async def test_generate_card_content_repairs_v13_title_issue_before_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_CARD_CONTENT_PROFILE_ID", raising=False)
    load_card_content_models.cache_clear()
    draft = seed_validation_draft(
        _candidate(
            title="Mobile conversion stuck at 2.1%",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="funnel-conversion",
            matched_subreddit="shopify",
            score=96,
            num_comments=42,
            signal_level="rising",
            listing_source="search:relevance:week",
            intent_tags=["优化"],
            quotes=[
                {
                    "text": "Our Shopify mobile conversion has been stuck at 2.1%, session replays show users drop at shipping.",
                    "community": "r/shopify",
                    "permalink": "https://www.reddit.com/r/shopify/comments/v13/q1",
                },
                {
                    "text": "Before redesigning, watch 20-30 mobile recordings and fix the obvious friction.",
                    "community": "r/ecommerce",
                    "permalink": "https://www.reddit.com/r/ecommerce/comments/v13/q2",
                },
            ],
        )
    )
    payloads = [
        {
            "core_scene": "Shopify 卖家的移动端转化率卡在 2.1%。",
            "supported_claim": "证据支持先看用户会话回放定位运费步骤摩擦。",
            "risk_bounds": "不能说所有 Shopify 店铺都有这个问题。",
        },
        {
            "title": "移动端转化率卡在2.1%，先看用户会话回放",
            "summary_line": "Shopify 卖家的移动端转化率卡在 2.1%，评论建议先看 20-30 条会话回放。",
            "audience": "移动端转化率卡住的 Shopify 卖家",
            "why_now": "讨论已经从泛泛改版，收窄到运费步骤和会话回放这类具体排查动作。",
            "preview_quote_permalink": "https://www.reddit.com/r/shopify/comments/v13/q1",
            "detail": {
                "flashpoint": "争议点是先改版整个移动端页面，还是先用会话回放定位运费步骤。",
                "fight_line": "改版派觉得页面体验整体不行，排查派认为先看用户卡在哪一步。",
                "why_test_now": "原帖给出 2.1% 转化率和会话回放证据。",
                "continue_signal": "继续看 shipping、session replay、mobile 这些词是不是重复出现。",
                "stop_signal": "如果后续只剩泛泛改版建议，没有具体步骤证据，可以先放过。",
            },
        },
        {
            "title": "Shopify 移动端转化卡住，卖家用会话回放查运费",
        },
        _precheck_payload(),
    ]
    seen_models: list[str] = []

    def factory(model: str, timeout: float) -> _FakeClient:
        seen_models.append(model)
        return _FakeClient(payloads)

    result = await generate_card_content(
        draft, client_factory=factory, allow_breakdown=False
    )

    assert seen_models == [
        "google/gemini-3-flash-preview",
        "deepseek/deepseek-v4-pro",
        "deepseek/deepseek-v4-pro",
        "deepseek/deepseek-v4-pro",
    ]
    assert result.title == "Shopify 移动端转化卡住，卖家用会话回放查运费"


@pytest.mark.asyncio
async def test_generate_card_content_keeps_draft_when_title_repair_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_CARD_CONTENT_PROFILE_ID", raising=False)
    load_card_content_models.cache_clear()
    draft = seed_validation_draft(
        _candidate(
            title="Mobile conversion stuck at 2.1%",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="funnel-conversion",
            matched_subreddit="shopify",
            score=96,
            num_comments=42,
            signal_level="rising",
            listing_source="search:relevance:week",
            intent_tags=["优化"],
            quotes=[
                {
                    "text": "Our Shopify mobile conversion has been stuck at 2.1%, session replays show users drop at shipping.",
                    "community": "r/shopify",
                    "permalink": "https://www.reddit.com/r/shopify/comments/v13/q1",
                },
                {
                    "text": "Before redesigning, watch 20-30 mobile recordings and fix the obvious friction.",
                    "community": "r/ecommerce",
                    "permalink": "https://www.reddit.com/r/ecommerce/comments/v13/q2",
                },
            ],
        )
    )
    raws = [
        json.dumps(
            {
                "core_scene": "Shopify 卖家的移动端转化率卡在 2.1%。",
                "supported_claim": "证据支持先看用户会话回放定位运费步骤摩擦。",
                "risk_bounds": "不能说所有 Shopify 店铺都有这个问题。",
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "title": "移动端转化率卡在2.1%，先看用户会话回放",
                "summary_line": "Shopify 卖家的移动端转化率卡在 2.1%，评论建议先看 20-30 条会话回放。",
                "audience": "移动端转化率卡住的 Shopify 卖家",
                "why_now": "讨论已经从泛泛改版，收窄到运费步骤和会话回放这类具体排查动作。",
                "preview_quote_permalink": "https://www.reddit.com/r/shopify/comments/v13/q1",
                "detail": {
                    "flashpoint": "争议点是先改版整个移动端页面，还是先用会话回放定位运费步骤。",
                    "fight_line": "改版派觉得页面体验整体不行，排查派认为先看用户卡在哪一步。",
                    "why_test_now": "原帖给出 2.1% 转化率和会话回放证据。",
                    "continue_signal": "继续看 shipping、session replay、mobile 这些词是不是重复出现。",
                    "stop_signal": "如果后续只剩泛泛改版建议，没有具体步骤证据，可以先放过。",
                },
            },
            ensure_ascii=False,
        ),
        "",
        json.dumps(_precheck_payload(), ensure_ascii=False),
    ]
    client = _RawSequenceClient(raws)

    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client, allow_breakdown=False
    )

    assert result.title == "移动端转化率卡在2.1%，先看用户会话回放"
    assert getattr(result, "_hotpost_precheck_result")["decision"] == "PASS"


@pytest.mark.asyncio
async def test_generate_card_content_routes_breakdown_to_v13_writer_when_production_profile_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_CARD_CONTENT_PROFILE_ID", raising=False)
    load_card_content_models.cache_clear()
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    payloads = [
        {
            "core_scene": "销售团队在讨论 CRM 回填负担。",
            "supported_claim": "证据只支持一线销售觉得回填占用时间。",
            "risk_bounds": "不能放大成所有团队都要迁移。",
        },
        {
            "title": "一线销售质疑 CRM 回填是在替流程补作业",
            "summary_line": "多条讨论都把 CRM 回填说成每天额外的行政负担。",
            "audience": "每天要补 CRM 字段的一线销售",
            "why_now": "多个社区都出现类似抱怨，并且已经有人提到更轻替代。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "销售觉得成交之外还要替系统补行政记录。",
                "target_user_and_scene": "一线销售推进客户后还要补 CRM 字段的场景。",
                "why_test_now": "证据里同时出现每天 30 分钟回填和评估替代方案。",
                "continue_signal": "继续看 CRM updates、lighter alternatives 这些词是不是重复出现。",
                "stop_signal": "如果后续只剩单帖吐槽，没有替代方案讨论，可以先放过。",
            },
        },
        {
            "title": "大家骂的是 CRM，真正烦的是替流程背责任",
            "summary_line": "表面看是在嫌 CRM 重，真正反复暴露的是：销售不觉得这一步在帮自己赢单。",
            "audience": "每天要回填 CRM 的一线销售",
            "why_now": "值得把这几条讨论放在一起看，因为两边都把问题指向同一件事：这一步不被当成自己的工作。",
            "thesis": "表面在骂录入麻烦，真正卡点是销售不认这一步的价值。",
            "writing_angle_or_perspective": "从“这件事到底算谁的工作”这个角度讲。",
            "tension_point_or_why_it_matters": "只盯着简化字段，会误以为这是 UI 问题。",
            "title_hooks": ["不是 CRM 太重，是销售根本不认这一步算自己的工作"],
            "quote_pack": [
                "I spend 30 min a day feeding Salesforce data.｜我每天要花 30 分钟喂 Salesforce 数据。｜r/sales",
                "CRM updates feel like admin work for my manager, not me.｜CRM 更新像是在替经理做行政活，不像在帮我。｜r/startups",
            ],
            "supporting_quote_permalinks": [
                "https://www.reddit.com/r/sales/comments/abc123/q1",
                "https://www.reddit.com/r/startups/comments/def456/q2",
            ],
        },
        _precheck_payload(),
    ]
    seen_models: list[str] = []

    def factory(model: str, timeout: float) -> _FakeClient:
        seen_models.append(model)
        return _FakeClient(payloads)

    result = await generate_card_content(draft, client_factory=factory)

    assert result.card_type == "write"
    assert seen_models == [
        "google/gemini-3-flash-preview",
        "deepseek/deepseek-v4-pro",
        "deepseek/deepseek-v4-pro",
        "deepseek/deepseek-v4-pro",
    ]
    assert "xiaomi/mimo-v2.5-pro" not in seen_models
    assert getattr(result, "_hotpost_precheck_result")["decision"] == "PASS"


@pytest.mark.asyncio
async def test_generate_card_content_passes_v13_semantic_brief_to_breakdown_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_CARD_CONTENT_PROFILE_ID", raising=False)
    load_card_content_models.cache_clear()
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    payloads = [
        {
            "core_scene": "销售团队在讨论 CRM 回填负担。",
            "actor_and_scene": "一线销售在推进客户后还要补 CRM 字段。",
            "supported_claim": "证据只支持一线销售觉得回填占用时间。",
            "evidence_basis": [
                {
                    "claim": "每天回填占用销售时间。",
                    "community": "r/sales",
                    "quote_text": "I spend 30 min a day feeding Salesforce data.",
                    "permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
                },
                {
                    "claim": "CRM 更新被感知为替经理做行政活。",
                    "community": "r/startups",
                    "quote_text": "CRM updates feel like admin work for my manager, not me.",
                    "permalink": "https://www.reddit.com/r/startups/comments/def456/q2",
                },
            ],
            "lane_specific": {
                "hot": {
                    "flashpoint": "不适用",
                    "debate_sides": "不适用",
                    "controversy_axis": "不适用",
                    "why_people_argue": "不适用",
                },
                "signal": {
                    "target_user": "一线销售",
                    "pain_trigger": "成交之外还要补行政记录。",
                    "buying_or_adoption_signal": "已经有人提到更轻替代。",
                    "testability": "观察 lighter alternatives 是否继续出现。",
                },
                "breakdown": {
                    "repeated_pattern": "多个社区都把 CRM 回填说成额外行政负担。",
                    "cross_thread_commonality": "都指向销售不认这一步的价值。",
                    "thesis_candidate": "表面在骂录入麻烦，真正卡点是销售不认这一步的价值。",
                    "synthesis_angle": "从这一步到底算谁的工作讲。",
                },
            },
            "tension_or_decision": "团队要在管理可见性和一线销售时间之间取舍。",
            "why_now_readout": "多社区同时出现同一类回填负担讨论。",
            "risk_bounds": "不能放大成所有团队都要迁移。",
            "writing_focus": "从这一步到底帮不帮销售赢单切入。",
            "avoid_claims": ["不要写成 CRM 行业整体崩了。"],
            "uncertainty": {
                "confidence": "medium",
                "missing_evidence": ["缺少真实迁移比例。"],
                "weak_points": ["样本仍以讨论帖为主。"],
                "single_thread_risk": "低，已有跨社区证据。",
            },
        },
        {
            "title": "一线销售质疑 CRM 回填是在替流程补作业",
            "summary_line": "多条讨论都把 CRM 回填说成每天额外的行政负担。",
            "audience": "每天要补 CRM 字段的一线销售",
            "why_now": "多个社区都出现类似抱怨，并且已经有人提到更轻替代。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "销售觉得成交之外还要替系统补行政记录。",
                "target_user_and_scene": "一线销售推进客户后还要补 CRM 字段的场景。",
                "why_test_now": "证据里同时出现每天 30 分钟回填和评估替代方案。",
                "continue_signal": "继续看 CRM updates、lighter alternatives 这些词是不是重复出现。",
                "stop_signal": "如果后续只剩单帖吐槽，没有替代方案讨论，可以先放过。",
            },
        },
        {
            "title": "大家骂的是 CRM，真正烦的是替流程背责任",
            "summary_line": "表面看是在嫌 CRM 重，真正反复暴露的是：销售不觉得这一步在帮自己赢单。",
            "audience": "每天要回填 CRM 的一线销售",
            "why_now": "值得把这几条讨论放在一起看，因为两边都把问题指向同一件事：这一步不被当成自己的工作。",
            "thesis": "表面在骂录入麻烦，真正卡点是销售不认这一步的价值。",
            "writing_angle_or_perspective": "从“这件事到底算谁的工作”这个角度讲。",
            "tension_point_or_why_it_matters": "只盯着简化字段，会误以为这是 UI 问题。",
            "title_hooks": ["不是 CRM 太重，是销售根本不认这一步算自己的工作"],
            "quote_pack": [
                "I spend 30 min a day feeding Salesforce data.｜我每天要花 30 分钟喂 Salesforce 数据。｜r/sales",
                "CRM updates feel like admin work for my manager, not me.｜CRM 更新像是在替经理做行政活，不像在帮我。｜r/startups",
            ],
            "supporting_quote_permalinks": [
                "https://www.reddit.com/r/sales/comments/abc123/q1",
                "https://www.reddit.com/r/startups/comments/def456/q2",
            ],
        },
        _precheck_payload(),
    ]
    clients: list[_RecordingClient] = []

    def factory(model: str, timeout: float) -> _RecordingClient:
        client = _RecordingClient(payloads)
        clients.append(client)
        return client

    result = await generate_card_content(draft, client_factory=factory)

    assert result.card_type == "write"
    assert len(clients) == 4
    breakdown_prompt = clients[2].messages[0]["content"]
    assert "## 语义理解层 brief" in breakdown_prompt
    assert "actor_and_scene" in breakdown_prompt
    assert "evidence_basis" in breakdown_prompt
    assert "buying_or_adoption_signal" in breakdown_prompt
    assert "missing_evidence" in breakdown_prompt
    assert "不要写成 CRM 行业整体崩了" in breakdown_prompt


@pytest.mark.asyncio
async def test_refresh_breakdown_content_routes_to_v13_writer_when_production_profile_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HOTPOST_CARD_CONTENT_PROFILE_ID", raising=False)
    load_card_content_models.cache_clear()
    source = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    draft = source.model_copy(
        update={
            "title": "一线销售开始质疑 CRM 回填是不是在替流程补作业",
            "summary_line": "多条讨论都把 CRM 回填说成每天额外的行政负担。",
            "audience": "每天要补 CRM 字段的一线销售",
            "why_now": "多个社区都出现类似抱怨，并且已经有人提到更轻替代。",
        }
    )
    breakdown_payload = {
        "title": "大家骂的是 CRM，真正烦的是替流程背责任",
        "summary_line": "表面看是在嫌 CRM 重，真正反复暴露的是：销售不觉得这一步在帮自己赢单。",
        "audience": "每天要回填 CRM 的一线销售",
        "why_now": "值得把这几条讨论放在一起看，因为两边都把问题指向同一件事：这一步不被当成自己的工作。",
        "thesis": "表面在骂录入麻烦，真正卡点是销售不认这一步的价值。",
        "writing_angle_or_perspective": "从“这件事到底算谁的工作”这个角度讲。",
        "tension_point_or_why_it_matters": "只盯着简化字段，会误以为这是 UI 问题。",
        "title_hooks": ["不是 CRM 太重，是销售根本不认这一步算自己的工作"],
        "quote_pack": [
            "I spend 30 min a day feeding Salesforce data.｜我每天要花 30 分钟喂 Salesforce 数据。｜r/sales",
            "CRM updates feel like admin work for my manager, not me.｜CRM 更新像是在替经理做行政活，不像在帮我。｜r/startups",
        ],
        "supporting_quote_permalinks": [
            "https://www.reddit.com/r/sales/comments/abc123/q1",
            "https://www.reddit.com/r/startups/comments/def456/q2",
        ],
    }
    seen_models: list[str] = []

    def factory(model: str, timeout: float) -> _FakeClient:
        seen_models.append(model)
        return _FakeClient([breakdown_payload])

    result = await refresh_breakdown_content(draft, client_factory=factory)

    assert result.card_type == "write"
    assert seen_models == ["deepseek/deepseek-v4-pro"]


@pytest.mark.asyncio
async def test_generate_card_content_can_disable_breakdown_for_published_refresh() -> None:
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    payloads = [
        {
            "title": "销售团队在吵：每天都在给 CRM 补作业",
            "summary_line": "有人嫌 CRM 很重，已经开始怀疑这套流程到底帮不帮自己。",
            "audience": "5-50 人团队里每天要回填 CRM 的一线销售",
            "why_now": "本周 r/sales 至少有 1 帖在讲这件事。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "销售觉得自己一直在替系统补作业。",
                "target_user_and_scene": "一线销售每天要补 CRM 字段的场景。",
                "why_test_now": "开始有人直接问替代方案。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看 CRM updates、lighter alternatives 这些词是不是继续出现。",
                "stop_signal": "如果后续没有更多具体场景，就不用放大。",
            },
        }
    ]

    result = await generate_card_content(
        draft,
        client_factory=lambda _model, _timeout: _FakeClient(payloads),
        allow_breakdown=False,
    )

    assert result.card_type == "validate"
    assert result.lane == draft.lane


@pytest.mark.asyncio
async def test_generate_card_content_retries_when_field_copy_hits_banned_pattern() -> None:
    draft = seed_validation_draft(_candidate())
    payloads = [
        {
            "title": "Cursor 用户开始算账了：只卖更快不一定值",
            "summary_line": "用户已经开始把速度和账单放在一起算。",
            "audience": "用 Cursor 写代码的开发者，特别是那些在意成本的人",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "用户觉得只为速度多付钱不值。",
                "target_user_and_scene": "每天用 Cursor 写代码、月底要看账单的开发者。",
                "why_test_now": "原话里已经把速度和成本放在一起比较。",
                "continue_signal": "继续看 Fast、Standard、bigger model 这些词会不会继续出现。",
                "stop_signal": "如果后续只剩单纯夸 Cursor，就不用放大。",
            },
        },
        {
            "title": "Cursor 用户开始算账了：只卖更快不一定值",
            "summary_line": "用户已经开始把速度和账单放在一起算。",
            "audience": "每天用 Cursor 写代码、月底要看账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "用户觉得只为速度多付钱不值。",
                "target_user_and_scene": "每天用 Cursor 写代码、月底要看账单的开发者。",
                "why_test_now": "原话里已经把速度和成本放在一起比较。",
                "continue_signal": "继续看 Fast、Standard、bigger model 这些词会不会继续出现。",
                "stop_signal": "如果后续只剩单纯夸 Cursor，就不用放大。",
            },
        },
    ]

    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
    )

    assert result.audience == "每天用 Cursor 写代码、月底要看账单的开发者"


@pytest.mark.asyncio
async def test_generate_card_content_uses_llm_why_test_now_as_evidence_readout() -> None:
    draft = seed_validation_draft(
        _candidate(
            topic_pack_id="agent-builder",
            matched_subreddit="cursor",
            top_communities=["r/cursor"],
            intent_tags=["趋势变化"],
        )
    )
    payloads = [
        {
            "title": "Cursor 用户开始算账了：只卖更快不一定值这个钱",
            "summary_line": "Cursor 用户开始把速度、账单和模型能力放在一起算，原话是“I would rather use a bigger model in that case”。",
            "audience": "写代码天天靠 AI、月底要比价的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "用户不是不愿意为 AI 编程工具付钱，而是不想只为更快买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底核算工具账单的开发者。",
                "why_test_now": "原话是“I would rather use a bigger model in that case”。翻过来就是：如果只是省时间但模型变弱，用户宁愿慢一点，也要更强的模型。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看 Composer 2 Fast、bigger model、cost reduction 这些词是不是继续出现。",
                "stop_signal": "如果后续只剩喜欢或不喜欢 Cursor，没有继续讨论套餐、速度和模型大小，就不用放大。",
            },
        }
    ]

    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
    )

    assert "I would rather use a bigger model" in result.detail.why_test_now
    assert "翻过来就是" in result.detail.why_test_now
    assert result.detail.why_test_now != result.why_now


@pytest.mark.asyncio
async def test_generate_card_content_blocks_why_test_now_repeating_system_why_now() -> None:
    draft = seed_validation_draft(
        _candidate(
            topic_pack_id="agent-builder",
            matched_subreddit="cursor",
            top_communities=["r/cursor"],
        )
    )
    payloads = [
        {
            "title": "Cursor 用户开始重新算加速档位值不值",
            "summary_line": "Cursor 用户开始把速度和账单放在一起算，有人宁愿慢一点，也想换更低成本。",
            "audience": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "开发者愿意为模型效果付钱，但不一定愿意只为速度溢价买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者。",
                "why_test_now": "r/cursor 这条原话已经把取舍说清楚了：用户开始重新算这件事还值不值。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看 Composer 2 Fast、bigger model、cost reduction 这些词是不是继续出现。",
                "stop_signal": "如果后续只剩喜欢或不喜欢 Cursor，没有继续讨论套餐、速度和模型大小，就不用放大。",
            },
        },
        {
            "title": "Cursor 用户开始重新算加速档位值不值",
            "summary_line": "Cursor 用户开始把速度和账单放在一起算，有人宁愿慢一点，也想换更低成本。",
            "audience": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "开发者愿意为模型效果付钱，但不一定愿意只为速度溢价买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者。",
                "why_test_now": "r/cursor 这条原话已经把取舍说清楚了：用户开始重新算这件事还值不值。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看 Composer 2 Fast、bigger model、cost reduction 这些词是不是继续出现。",
                "stop_signal": "如果后续只剩喜欢或不喜欢 Cursor，没有继续讨论套餐、速度和模型大小，就不用放大。",
            },
        },
    ]

    with pytest.raises(ValueError, match="why_test_now contains banned pattern"):
        await generate_card_content(
            draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
        )


@pytest.mark.asyncio
async def test_generate_card_content_requires_llm_continue_and_stop_signal() -> None:
    draft = seed_validation_draft(_candidate())
    payloads = [
        {
            "title": "销售团队在吵：每天都在给 CRM 补作业",
            "summary_line": "CRM 回填已经不是小麻烦，销售开始怀疑这套流程到底帮不帮成交。",
            "audience": "每天要补 CRM 字段的一线销售",
            "why_now": "本周 r/sales 至少 1 帖在讲这件事。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "销售觉得自己一直在替系统补作业。",
                "target_user_and_scene": "一线销售每天要在成交之外补 CRM 字段。",
                "why_test_now": "开始有人直接问替代方案。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "",
                "stop_signal": "",
            },
        },
        {
            "title": "销售团队在吵：每天都在给 CRM 补作业",
            "summary_line": "CRM 回填已经不是小麻烦，销售开始怀疑这套流程到底帮不帮成交。",
            "audience": "每天要补 CRM 字段的一线销售",
            "why_now": "本周 r/sales 至少 1 帖在讲这件事。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "销售觉得自己一直在替系统补作业。",
                "target_user_and_scene": "一线销售每天要在成交之外补 CRM 字段。",
                "why_test_now": "开始有人直接问替代方案。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "",
                "stop_signal": "",
            },
        },
    ]

    with pytest.raises(ValueError, match="continue_signal is empty"):
        await generate_card_content(
            draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
        )


@pytest.mark.asyncio
async def test_generate_card_content_blocks_reporty_summary_line_pattern() -> None:
    draft = seed_validation_draft(_candidate())
    payloads = [
        {
            "title": "Cursor 用户开始重新算加速档位值不值",
            "summary_line": "这帖吵的不是 Cursor 好不好用，而是 Composer 2 Fast 这个档位到底值不值。",
            "audience": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "开发者愿意为模型效果付钱，但不一定愿意只为速度溢价买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者。",
                "why_test_now": "有人已经说宁愿慢一点换更低成本。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看 Composer 2 Fast、bigger model、cost reduction 这些词是不是继续出现。",
                "stop_signal": "如果后续只剩喜欢或不喜欢 Cursor，没有继续讨论套餐、速度和模型大小，就不用放大。",
            },
        },
        {
            "title": "Cursor 用户开始重新算加速档位值不值",
            "summary_line": "这帖吵的不是 Cursor 好不好用，而是 Composer 2 Fast 这个档位到底值不值。",
            "audience": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "开发者愿意为模型效果付钱，但不一定愿意只为速度溢价买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者。",
                "why_test_now": "有人已经说宁愿慢一点换更低成本。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看 Composer 2 Fast、bigger model、cost reduction 这些词是不是继续出现。",
                "stop_signal": "如果后续只剩喜欢或不喜欢 Cursor，没有继续讨论套餐、速度和模型大小，就不用放大。",
            },
        },
    ]

    with pytest.raises(
        ValueError, match="summary_line contains banned pattern: 这帖吵的不是"
    ):
        await generate_card_content(
            draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
        )


@pytest.mark.asyncio
async def test_generate_card_content_blocks_generic_continue_and_stop_signal() -> None:
    draft = seed_validation_draft(_candidate())
    payloads = [
        {
            "title": "Cursor 用户开始重新算加速档位值不值",
            "summary_line": "Cursor 用户开始把速度和账单放在一起算，有人宁愿慢一点，也想换更低成本。",
            "audience": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "开发者愿意为模型效果付钱，但不一定愿意只为速度溢价买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者。",
                "why_test_now": "有人已经说宁愿慢一点换更低成本。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "如果接下来在更多社区里还出现同样抱怨，就继续盯。",
                "stop_signal": "如果后面只剩零散吐槽，没有新的具体场景或后续追问，就先放过。",
            },
        },
        {
            "title": "Cursor 用户开始重新算加速档位值不值",
            "summary_line": "Cursor 用户开始把速度和账单放在一起算，有人宁愿慢一点，也想换更低成本。",
            "audience": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "开发者愿意为模型效果付钱，但不一定愿意只为速度溢价买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者。",
                "why_test_now": "有人已经说宁愿慢一点换更低成本。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "如果接下来在更多社区里还出现同样抱怨，就继续盯。",
                "stop_signal": "如果后面只剩零散吐槽，没有新的具体场景或后续追问，就先放过。",
            },
        },
    ]

    with pytest.raises(ValueError, match="continue_signal contains banned pattern"):
        await generate_card_content(
            draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
        )


@pytest.mark.asyncio
async def test_generate_card_content_rewrites_mechanical_ai_transitions() -> None:
    draft = seed_validation_draft(_candidate())
    payloads = [
        {
            "title": "Cursor 用户开始重新算加速档位值不值",
            "summary_line": "首先，Cursor 用户开始把速度和账单放在一起算，有人宁愿慢一点，也想换更低成本。",
            "audience": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者",
            "why_now": "用户开始把速度和账单放在一起算。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "开发者愿意为模型效果付钱，但不一定愿意只为速度溢价买单。",
                "target_user_and_scene": "每天靠 Cursor 写代码、月底会算 AI 工具账单的开发者。",
                "why_test_now": "有人已经说宁愿慢一点换更低成本。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看 Composer 2 Fast、bigger model、cost reduction 这些词是不是继续出现。",
                "stop_signal": "如果后续只剩喜欢或不喜欢 Cursor，没有继续讨论套餐、速度和模型大小，就不用放大。",
            },
        }
    ]

    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
    )

    assert not result.summary_line.startswith("首先")
    assert result.summary_line.startswith("Cursor 用户开始把速度和账单")


@pytest.mark.asyncio
async def test_generate_card_content_blocks_low_quality_signal_input() -> None:
    draft = seed_validation_draft(
        _candidate(
            quotes=[
                {
                    "text": "Hi, hit me up if you ever want to chat",
                    "community": "r/ChatGPT",
                    "permalink": "https://www.reddit.com/r/ChatGPT/comments/weak/q1",
                }
            ]
        )
    )
    with pytest.raises(ValueError, match="Signal input quality gate blocked draft"):
        await generate_card_content(
            draft, client_factory=lambda _model, _timeout: _FakeClient([])
        )


@pytest.mark.asyncio
async def test_generate_card_content_allows_hot_draft_to_bypass_signal_input_gate() -> None:
    draft = seed_validation_draft(
        _candidate(
            title="SEMrush charged me $211 using deceptive dark patterns to prevent trial cancellation",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="organic-discovery",
            matched_subreddit="SEO",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
            quotes=[
                {
                    "text": "Classic SEMrush. Predatory company and the cancellation flow is clearly designed to trap you.",
                    "community": "r/SEO",
                    "permalink": "https://www.reddit.com/r/SEO/comments/hot/q1",
                },
                {
                    "text": "A chargeback is the only thing that worked for me because support kept looping me around.",
                    "community": "r/SEO",
                    "permalink": "https://www.reddit.com/r/SEO/comments/hot/q2",
                },
            ],
        )
    )
    payloads = [
        {
            "title": "SEMrush 这波火，不是因为 211 美元贵，而是取消试用像故意设障。",
            "summary_line": "评论区吵起来的点不是贵不贵，而是很多人都把这套取消流程看成故意卡人。",
            "audience": "在评估 SEO 工具、又担心订阅和续费套路的从业者。",
            "why_now": "讨论已经不是个体吐槽，而是在追问这种收费和取消方式到底算不算 dark pattern。",
            "preview_quote_permalink": "https://www.reddit.com/r/SEO/comments/hot/q1",
            "detail": {
                "flashpoint": "这帖突然炸起来，不是因为 211 美元贵，而是很多人都觉得取消试用像故意设障。",
                "fight_line": "评论区吵的不是价钱本身，而是这种收费和取消方式到底算不算故意卡人。",
                "why_test_now": "这帖火起来后，讨论点已经从价格走到了规则和信任问题。",
                "continue_signal": "如果更多工具都被拿来对比收费和取消套路，这条线值得继续盯。",
                "stop_signal": "如果后续只剩情绪化抱怨、没有更多具体案例，可以先放过。",
            },
        }
    ]
    result = await generate_card_content(
        draft,
        client_factory=lambda _model, _timeout: _FakeClient(payloads),
        allow_breakdown=False,
    )
    assert result.lane == "hot"
    assert result.title.startswith("SEMrush 这波火")
    assert result.why_now == "讨论已经不是个体吐槽，而是在追问这种收费和取消方式到底算不算 dark pattern。"


@pytest.mark.asyncio
async def test_generate_card_content_uses_hot_mode_prompt_for_hot_lane() -> None:
    draft = seed_validation_draft(
        _candidate(
            title="SEO is over and now we have GEO",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="organic-discovery",
            matched_subreddit="DigitalMarketing",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
            quotes=[
                {
                    "text": "The thread is no longer debating a new acronym, it is arguing whether the SEO playbook still works at all.",
                    "community": "r/DigitalMarketing",
                    "permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q1",
                },
                {
                    "text": "People are split between adapting the old SEO stack and rebuilding for answer engines from scratch.",
                    "community": "r/DigitalMarketing",
                    "permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q2",
                },
            ],
        )
    )
    client = _RecordingClient(
        [
            {
                "title": "GEO 一冒头，DigitalMarketing 里吵的已经不是新术语，而是 SEO 那套到底还够不够用。",
                "summary_line": "这帖火起来后，争论点很集中：一拨人觉得 SEO 只是换个壳，另一拨人已经想重做整套内容和分发。",
                "audience": "正在重看搜索获客打法的人",
                "why_now": "这波讨论已经从概念科普，走到了老方法还顶不顶用的路线分歧。",
                "preview_quote_permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q1",
                "detail": {
                    "flashpoint": "这帖突然炸起来，不是因为 GEO 这个词新，而是因为大家开始怀疑老 SEO 还顶不顶用。",
                    "fight_line": "评论区分成两派：一派想继续修旧 SEO，另一派觉得该按答案引擎重做内容和分发。",
                    "why_test_now": "讨论已经从学概念变成站队。",
                    "continue_signal": "如果更多团队开始公开重写玩法，这条线值得继续盯。",
                    "stop_signal": "如果后续只剩转述，没有新的分歧和案例，可以先放过。",
                },
            }
        ]
    )
    result = await generate_card_content(
        draft,
        client_factory=lambda _model, _timeout: client,
        allow_breakdown=False,
    )
    assert "当前输出模式：近期爆帖" in client.messages[0]["content"]
    assert "这帖为什么突然火了" in client.messages[0]["content"]
    assert "火的是这条帖，不一定是整个行业" in client.messages[0]["content"]
    assert "一张热点卡只回答两件事" in client.messages[0]["content"]
    assert "不要借一条热帖偷渡大结论" in client.messages[0]["content"]
    assert "audience 只写一个自然的人群短语，不写解释句，不超过一行" in client.messages[0]["content"]
    assert "潜力快帖字段边界" not in client.messages[0]["content"]
    assert "为什么现在发生变化" not in client.messages[0]["content"]
    assert "flashpoint" in client.messages[1]["content"]
    assert "fight_line" in client.messages[1]["content"]
    assert "pain_point" not in client.messages[1]["content"]
    assert "target_user_and_scene" not in client.messages[1]["content"]
    assert "why_now_reason" not in client.messages[1]["content"]
    assert "current_title" not in client.messages[1]["content"]
    assert result.detail.model_dump()["flashpoint"].startswith("这帖突然炸起来")
    assert result.detail.model_dump()["fight_line"].startswith("评论区分成两派")


@pytest.mark.asyncio
async def test_generate_card_content_routes_hot_lane_to_gemini3_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOTPOST_CARD_CONTENT_PROFILE_ID", "off")
    load_card_content_models.cache_clear()
    draft = seed_validation_draft(
        _candidate(
            title="SEO is over and now we have GEO",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="organic-discovery",
            matched_subreddit="DigitalMarketing",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
            quotes=[
                {
                    "text": "The thread is no longer debating a new acronym, it is arguing whether the SEO playbook still works at all.",
                    "community": "r/DigitalMarketing",
                    "permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q1",
                },
                {
                    "text": "People are split between adapting the old SEO stack and rebuilding for answer engines from scratch.",
                    "community": "r/DigitalMarketing",
                    "permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q2",
                },
            ],
        )
    )
    calls: list[tuple[str, float]] = []
    payloads = [
        {
            "title": "GEO 一冒头，DigitalMarketing 里吵的已经不是新术语，而是 SEO 那套到底还够不够用。",
            "summary_line": "这帖火起来后，争论点很集中：一拨人觉得 SEO 只是换个壳，另一拨人已经想重做整套内容和分发。",
            "audience": "正在重看搜索获客打法的人",
            "why_now": "这波讨论已经从概念科普，走到了老方法还顶不顶用的路线分歧。",
            "preview_quote_permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q1",
            "detail": {
                "flashpoint": "这帖突然炸起来，不是因为 GEO 这个词新，而是因为大家开始怀疑老 SEO 还顶不顶用。",
                "fight_line": "评论区分成两派：一派想继续修旧 SEO，另一派觉得该按答案引擎重做内容和分发。",
                "why_test_now": "讨论已经从学概念变成站队。",
                "continue_signal": "如果更多团队开始公开重写玩法，这条线值得继续盯。",
                "stop_signal": "如果后续只剩转述，没有新的分歧和案例，可以先放过。",
            },
        }
    ]

    def factory(model: str, timeout: float) -> _FakeClient:
        calls.append((model, timeout))
        return _FakeClient(payloads)

    await generate_card_content(
        draft,
        client_factory=factory,
        allow_breakdown=False,
    )
    load_card_content_models.cache_clear()
    assert calls[0] == ("google/gemini-3-flash-preview", 22.0)


def test_build_hot_prompt_uses_hot_detail_schema() -> None:
    draft = seed_validation_draft(
        _candidate(
            title="Why everyone is suddenly arguing about GEO",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="organic-discovery",
            matched_subreddit="DigitalMarketing",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
        )
    )

    messages = build_hot_prompt(draft, banned_patterns=["套话"], field_contract_prompt="")

    assert '"flashpoint":"string"' in messages[1]["content"]
    assert '"fight_line":"string"' in messages[1]["content"]
    assert '"pain_point":"string"' not in messages[1]["content"]
    assert '"target_user_and_scene":"string"' not in messages[1]["content"]


def test_build_hot_prompt_payload_only_keeps_hot_generation_inputs() -> None:
    draft = seed_validation_draft(
        _candidate(
            title="Why everyone is suddenly arguing about GEO",
            source_scope_id="business-growth-ops",
            source_scope_name="商业增长与运营",
            topic_pack_id="organic-discovery",
            matched_subreddit="DigitalMarketing",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
            quotes=[
                {
                    "text": "The thread is no longer debating a new acronym, it is arguing whether the SEO playbook still works at all.",
                    "community": "r/DigitalMarketing",
                    "permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q1",
                },
                {
                    "text": "People are split between adapting the old SEO stack and rebuilding for answer engines from scratch.",
                    "community": "r/DigitalMarketing",
                    "permalink": "https://www.reddit.com/r/DigitalMarketing/comments/hot/q2",
                },
            ],
        )
    )

    messages = build_hot_prompt(draft, banned_patterns=["套话"], field_contract_prompt="")
    user_payload = json.loads(messages[1]["content"])

    assert user_payload["scope"] == "商业增长与运营"
    assert user_payload["stats"] == {
        "thread_count": 1,
        "community_count": 1,
        "intent_tags": ["趋势变化"],
    }
    assert "card_type_requested" not in user_payload
    assert "source_scope_id" not in user_payload
    assert "source_scope_name" not in user_payload
    assert "matched_subreddit" not in user_payload
    assert "source_communities" not in user_payload
    assert "quote_count" not in user_payload
    assert "signal_level" not in user_payload
    assert "source_link" not in user_payload


def test_build_breakdown_prompt_uses_breakdown_output_schema() -> None:
    draft = seed_validation_draft(
        _candidate(
            title="Sales reps hate feeding Salesforce",
            source_scope_id="ai-automation",
            source_scope_name="AI 与自动化",
            topic_pack_id="agent-builder",
            matched_subreddit="sales",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
            thread_count=3,
            community_count=2,
        )
    )

    messages = build_breakdown_prompt(
        draft, banned_patterns=["套话"], field_contract_prompt=""
    )

    assert '"thesis":"string"' in messages[1]["content"]
    assert '"writing_angle_or_perspective":"string"' in messages[1]["content"]
    assert '"tension_point_or_why_it_matters":"string"' in messages[1]["content"]
    assert '"audience":"string"' in messages[1]["content"]
    assert '"why_now":"string"' in messages[1]["content"]
    assert '"pain_point":"string"' not in messages[1]["content"]
    assert '"target_user_and_scene":"string"' not in messages[1]["content"]


def test_build_breakdown_prompt_payload_only_keeps_breakdown_generation_inputs() -> (
    None
):
    draft = seed_validation_draft(
        _candidate(
            title="Sales reps hate feeding Salesforce",
            source_scope_id="ai-automation",
            source_scope_name="AI 与自动化",
            topic_pack_id="agent-builder",
            matched_subreddit="sales",
            score=180,
            num_comments=86,
            signal_level="rising",
            listing_source="listing:hot:day",
            intent_tags=["趋势变化"],
            thread_count=3,
            community_count=2,
            quotes=[
                {
                    "text": "I spend 30 min a day feeding Salesforce data.",
                    "community": "r/sales",
                    "permalink": "https://www.reddit.com/r/sales/comments/break/q1",
                },
                {
                    "text": "CRM updates feel like admin work for my manager, not me.",
                    "community": "r/startups",
                    "permalink": "https://www.reddit.com/r/startups/comments/break/q2",
                },
            ],
        )
    )

    messages = build_breakdown_prompt(
        draft, banned_patterns=["套话"], field_contract_prompt=""
    )
    user_payload = json.loads(messages[1]["content"])

    assert user_payload["scope"] == "AI 与自动化"
    assert user_payload["stats"] == {
        "thread_count": 3,
        "community_count": 2,
        "intent_tags": ["趋势变化"],
    }
    assert user_payload["current_card"] == {
        "card_type": "validate",
        "title": draft.title,
        "summary_line": draft.summary_line,
        "audience": draft.audience,
        "why_now": draft.why_now,
    }
    assert "source_scope_id" not in user_payload
    assert "source_scope_name" not in user_payload
    assert "signal_level" not in user_payload
    assert "signal_card" not in user_payload


@pytest.mark.asyncio
async def test_refresh_breakdown_content_keeps_write_shape() -> None:
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    signal_payload = {
        "title": "销售团队在吵：每天都在给 CRM 补作业",
        "summary_line": "r/sales 有人说“我每天要花 30 分钟喂 Salesforce 数据”。这一周里，多个帖子都在讲回填负担。",
        "audience": "5-50 人团队里每天要回填 CRM 的一线销售",
        "why_now": "本周 r/sales 和 r/startups 都有类似帖子，讨论已经明确出现替代。",
        "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
        "detail": {
            "pain_point": "表面在抱怨录入，底下是在抱怨时间被系统吃掉。",
            "target_user_and_scene": "一线销售在推进客户同时还得回填 CRM 的场景。",
            "why_test_now": "多帖、多社区都在重复这类负担，已经不是孤例。",
            "continue_signal": "如果后续继续出现替代询问和流程减负诉求，值得继续追。",
            "stop_signal": "如果后续只有单点吐槽，没有更多具体场景，就先别上升。",
        },
    }
    breakdown_payload = {
        "title": "大家骂的是 CRM，真正烦的是替流程背责任",
        "summary_line": "表面看是在嫌 CRM 重，真正反复暴露的是：销售不觉得这一步在帮自己赢单，只觉得在替流程背责任。",
        "audience": "每天要回填 CRM 的一线销售",
        "why_now": "值得把这几条讨论放在一起看，不是因为又有人吐槽 CRM，而是两边都把问题指向了同一件事：这一步根本不被当成自己的工作。",
        "thesis": "表面在骂录入麻烦，真正卡点是销售不认这一步的价值，只把它当成替管理层做记录。",
        "writing_angle_or_perspective": "从“这件事到底算谁的工作”这个角度讲，会比继续讲工具轻重更准。",
        "tension_point_or_why_it_matters": "如果你只盯着简化字段，会误以为这是 UI 问题；原话真正指向的是责任感不归属。",
        "title_hooks": ["不是 CRM 太重，是销售根本不认这一步算自己的工作"],
        "quote_pack": [
            "I spend 30 min a day feeding Salesforce data.｜我每天要花 30 分钟喂 Salesforce 数据。｜r/sales",
            "CRM updates feel like admin work for my manager, not me.｜CRM 更新像是在替经理做行政活，不像在帮我。｜r/startups",
        ],
        "supporting_quote_permalinks": [
            "https://www.reddit.com/r/sales/comments/abc123/q1",
            "https://www.reddit.com/r/startups/comments/def456/q2",
        ],
    }
    client = _FakeClient([signal_payload, breakdown_payload])

    generated = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client
    )
    refreshed = await refresh_breakdown_content(
        generated,
        client_factory=lambda _model, _timeout: _FakeClient([breakdown_payload]),
    )

    assert refreshed.card_type == "write"
    assert refreshed.lane == "breakdown"
    assert refreshed.detail.thesis.startswith("表面在骂录入麻烦")
    assert refreshed.audience == "每天要回填 CRM 的一线销售"
    assert refreshed.why_now.startswith("值得把这几条讨论放在一起看")


@pytest.mark.asyncio
async def test_generate_card_content_uses_paid_econ_pack_variant_in_production() -> None:
    draft = seed_validation_draft(_paid_econ_candidate())
    client = _RecordingClient(
        [
            {
                "title": "离线转化设为主目标后，投手开始怀疑这笔投放还值不值",
                "summary_line": "ROAS 从 7x 掉到 2x，导入转化量也撑不起现在这套投放逻辑。",
                "audience": "管理高预算 PPC 账户的广告投手",
                "why_now": "讨论已经从排查掉量，转到要不要把主目标切回去。",
                "preview_quote_permalink": "https://www.reddit.com/r/PPC/comments/ppc123/q1",
                "detail": {
                    "pain_point": "主目标一切，投放表现和回传量一起掉下来。",
                    "target_user_and_scene": "刚把广告主目标切到离线转化、结果 ROAS 明显下滑的账户场景。",
                    "why_test_now": "有人直接把 7x 掉到 2x 的账摊出来，说明这不是轻微波动。",
                    "min_test_action": "去看原始讨论",
                    "continue_signal": "继续看后面会不会有人晒目标切换前后的 ROAS 和回传量。",
                    "stop_signal": "如果后面没有新的账户对比，只剩个别抱怨，就先别放大。",
                },
            }
        ]
    )
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client
    )
    assert "这是投放经济信号" in client.messages[0]["content"]
    assert "值不值" in result.title
    assert "ROAS" in result.summary_line
    assert "主目标" in result.why_now


@pytest.mark.asyncio
async def test_generate_card_content_routes_paid_economics_to_preview_fast_model() -> None:
    draft = seed_validation_draft(_paid_econ_candidate())
    calls: list[tuple[str, float]] = []
    payloads = [
        {
            "title": "离线转化设为主目标后，投手开始怀疑这笔投放还值不值",
            "summary_line": "ROAS 从 7x 掉到 2x，导入转化量也撑不起现在这套投放逻辑。",
            "audience": "管理高预算 PPC 账户的广告投手",
            "why_now": "讨论已经从排查掉量，转到要不要把主目标切回去。",
            "preview_quote_permalink": "https://www.reddit.com/r/PPC/comments/ppc123/q1",
            "detail": {
                "pain_point": "主目标一切，投放表现和回传量一起掉下来。",
                "target_user_and_scene": "刚把广告主目标切到离线转化、结果 ROAS 明显下滑的账户场景。",
                "why_test_now": "有人直接把 7x 掉到 2x 的账摊出来，说明这不是轻微波动。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "继续看后面会不会有人晒目标切换前后的 ROAS 和回传量。",
                "stop_signal": "如果后面没有新的账户对比，只剩个别抱怨，就先别放大。",
            },
        }
    ]

    def factory(model: str, timeout: float) -> _FakeClient:
        calls.append((model, timeout))
        return _FakeClient(payloads)

    await generate_card_content(draft, client_factory=factory)
    expected_timeout = float(load_card_content_rules()["timeouts"]["signal_seconds"])
    assert calls[0] == ("deepseek/deepseek-v4-flash", expected_timeout)


@pytest.mark.asyncio
async def test_generate_card_content_does_not_apply_paid_econ_variant_to_other_packs() -> None:
    draft = seed_validation_draft(
        _candidate(score=1, num_comments=1, signal_level="sustained")
    )
    client = _RecordingClient(
        [
            {
                "title": "销售团队在吵：每天都在给 CRM 补作业",
                "summary_line": "有人嫌 CRM 很重，已经开始怀疑这套流程到底帮不帮自己。",
                "audience": "5-50 人团队里每天要回填 CRM 的一线销售",
                "why_now": "本周 r/sales 至少有 1 帖在讲这件事。",
                "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
                "detail": {
                    "pain_point": "销售觉得自己一直在替系统补作业。",
                    "target_user_and_scene": "一线销售每天要补 CRM 字段的场景。",
                    "why_test_now": "开始有人直接问替代方案。",
                    "min_test_action": "去看原始讨论",
                    "continue_signal": "如果更多人继续问替代方案，就继续盯。",
                    "stop_signal": "如果后续没有更多具体场景，就先放过。",
                },
            }
        ]
    )
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client
    )
    assert "R站资深专家" in client.messages[0]["content"]
    assert "把 Reddit 真实讨论翻成国内用户一眼能懂的中文判断" in client.messages[0]["content"]
    assert "当前输出模式：潜力快帖" in client.messages[0]["content"]
    assert "title 先写业务后果，再点出设置或回传问题" not in client.messages[0]["content"]
    assert result.why_now != "讨论已经从报错排查走到‘电话成交怎么回传广告后台’，说明智能出价和 CPC 判断都会被带偏。"


@pytest.mark.asyncio
async def test_generate_card_content_applies_business_growth_scope_polish_without_touching_paid_econ() -> None:
    draft = seed_validation_draft(_business_growth_candidate())
    client = _RecordingClient(
        [
            {
                "title": "Reddit广告被直指80%+点击欺诈的最糟营销支出",
                "summary_line": "这意味着Reddit广告易陷80%+点击欺诈，成为绝对最差预算选择，从业者已开始重新评估其价值。",
                "audience": "投放者",
                "why_now": "本周 r/marketing 有 1 帖提到这件事。",
                "preview_quote_permalink": "https://www.reddit.com/r/marketing/comments/1sbspma/q1",
                "detail": {
                    "pain_point": "点击质量被怀疑，预算开始站不住。",
                    "target_user_and_scene": "投放者在重算渠道价值。",
                    "why_test_now": "讨论开始追问预算该不该继续留在这里。",
                    "min_test_action": "去看原始讨论",
                    "continue_signal": "如果更多人继续质疑渠道质量，就继续盯。",
                    "stop_signal": "如果后续没有更多具体场景，就先放过。",
                },
            }
        ]
    )
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client
    )
    assert "点击欺诈" in result.title
    assert "绝对最差预算选择" in result.summary_line
    assert "主要优化目标" not in (result.title + result.summary_line + result.why_now)
    assert "线下成交" not in (result.title + result.summary_line + result.why_now)


@pytest.mark.asyncio
async def test_generate_card_content_applies_selection_signal_pack_rules() -> None:
    candidate = CandidatePack.model_validate(
        {
            **_candidate().model_dump(mode="json"),
            "candidate_id": "cand-selection-001",
            "signal_id": "sig-selection-001",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商与卖家",
            "topic_pack_id": "selection-signals",
            "matched_subreddit": "BuyItForLife",
            "title": "Finding Thermal Shock Resistant Glass Drink Dispenser?",
            "matched_keywords": ["better alternative"],
            "top_communities": ["r/BuyItForLife"],
            "intent_tags": ["求推荐"],
            "evidence_quotes": [
                {
                    "text": "Stainless steel is the way to go. Check out Sansone.",
                    "community": "r/BuyItForLife",
                    "permalink": "https://www.reddit.com/r/BuyItForLife/comments/1seeom8/q1",
                },
                {
                    "text": "Nothing tempered will continue to be with a hole drilled into it for a spout.",
                    "community": "r/BuyItForLife",
                    "permalink": "https://www.reddit.com/r/BuyItForLife/comments/1seeom8/q2",
                },
            ],
        }
    )
    draft = seed_validation_draft(candidate)
    client = _RecordingClient(
        [
            {
                "title": "找耐热玻璃饮料桶，但打孔后很容易裂。",
                "summary_line": "帖子里有人说钻孔后的钢化玻璃根本扛不住喷嘴结构，另一位直接推荐不锈钢。",
                "audience": "想买耐用饮料桶的人",
                "why_now": "本周 r/BuyItForLife 有 1 帖在聊这件事。",
                "preview_quote_permalink": "https://www.reddit.com/r/BuyItForLife/comments/1seeom8/q1",
                "detail": {
                    "pain_point": "玻璃桶喷嘴口容易成为脆弱点。",
                    "target_user_and_scene": "在耐用品社区找饮料桶替代方案的买家。",
                    "why_test_now": "有人开始直接问替代方案。",
                    "min_test_action": "去看原始讨论",
                    "continue_signal": "如果更多人开始问替代材料，就继续盯。",
                    "stop_signal": "如果后续没有更多具体场景，就先放过。",
                },
            }
        ]
    )
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client
    )
    assert "这是选品信号" in client.messages[0]["content"]
    assert "饮料桶" in result.title
    assert "不锈钢" in result.summary_line
    assert "袜子" not in result.title + result.summary_line


@pytest.mark.asyncio
async def test_generate_card_content_blocks_unsupported_pack_term_from_readout() -> None:
    candidate = CandidatePack.model_validate(
        {
            **_candidate().model_dump(mode="json"),
            "candidate_id": "cand-selection-unsupported-term",
            "signal_id": "sig-selection-unsupported-term",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商与卖家",
            "topic_pack_id": "selection-signals",
            "matched_subreddit": "BuyItForLife",
            "title": "Finding Thermal Shock Resistant Glass Drink Dispenser?",
            "matched_keywords": ["better alternative"],
            "top_communities": ["r/BuyItForLife"],
            "intent_tags": ["求推荐"],
            "evidence_quotes": [
                {
                    "text": "Stainless steel is the way to go. Check out Sansone.",
                    "community": "r/BuyItForLife",
                    "permalink": "https://www.reddit.com/r/BuyItForLife/comments/1seeom8/q1",
                },
                {
                    "text": "Nothing tempered will continue to be with a hole drilled into it for a spout.",
                    "community": "r/BuyItForLife",
                    "permalink": "https://www.reddit.com/r/BuyItForLife/comments/1seeom8/q2",
                },
            ],
        }
    )
    draft = seed_validation_draft(candidate)
    payloads = [
        {
            "title": "大家开始找一双真正耐穿的袜子",
            "summary_line": "买家已经把袜子品牌口碑当成耐用底线。",
            "audience": "想买耐用品的用户",
            "why_now": "讨论开始追问替代方案。",
            "preview_quote_permalink": "https://www.reddit.com/r/BuyItForLife/comments/1seeom8/q1",
            "detail": {
                "pain_point": "玻璃桶喷嘴口容易成为脆弱点。",
                "target_user_and_scene": "在耐用品社区找饮料桶替代方案的买家。",
                "why_test_now": "有人开始直接问替代方案。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "如果更多人开始问替代材料，就继续盯。",
                "stop_signal": "如果后续没有更多具体场景，就先放过。",
            },
        }
    ]

    with pytest.raises(ValueError, match="unsupported term: 袜子"):
        await generate_card_content(
            draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
        )


@pytest.mark.asyncio
async def test_generate_card_content_applies_agent_builder_pack_rules() -> None:
    candidate = _agent_builder_candidate()
    draft = seed_validation_draft(candidate)
    client = _RecordingClient(
        [
            {
                "title": "Reddit 上有人觉得 agent 能力被吹得太过。",
                "summary_line": "讨论里有人说 agent 只在很窄的场景里才有效，而且 prompt engineering 很重。",
                "audience": "尝试把 AI agent 接进自动化流程的人",
                "why_now": "本周 r/automation 有 1 帖在聊这件事。",
                "preview_quote_permalink": "https://www.reddit.com/r/automation/comments/1saabgz/q1",
                "detail": {
                    "pain_point": "落地成本和维护负担高。",
                    "target_user_and_scene": "试图把 AI agent 接进真实自动化流程的人。",
                    "why_test_now": "大家开始重新算成本。",
                    "min_test_action": "去看原始讨论",
                    "continue_signal": "如果更多人开始谈成本，就继续盯。",
                    "stop_signal": "如果后续没有更多具体场景，就先放过。",
                },
            }
        ]
    )
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client
    )
    assert "agent" in result.title
    assert "prompt engineering" not in result.summary_line
    assert "r/automation" in result.why_now


@pytest.mark.asyncio
async def test_generate_card_content_routes_upstream_winds_to_preview_fast_model() -> None:
    candidate = CandidatePack.model_validate(
        {
            **_candidate().model_dump(mode="json"),
            "candidate_id": "cand-upstream-001",
            "signal_id": "sig-upstream-001",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "upstream-winds",
            "matched_subreddit": "artificial",
            "title": "Safety model launches are starting as invite-only again",
            "matched_keywords": ["invite only safety rollout"],
            "top_communities": ["r/artificial"],
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {
                    "text": "The company seems more worried about misuse than benchmark scores right now.",
                    "community": "r/artificial",
                    "permalink": "https://www.reddit.com/r/artificial/comments/up123/q1",
                },
                {
                    "text": "Rolling out to a tiny group first looks like boundary testing, not a full launch.",
                    "community": "r/artificial",
                    "permalink": "https://www.reddit.com/r/artificial/comments/up123/q2",
                },
            ],
        }
    )
    draft = seed_validation_draft(candidate)
    calls: list[tuple[str, float]] = []
    payloads = [
        {
            "title": "安全模型越危险，厂商越想先关在邀请制里摸清滥用边界",
            "summary_line": "讨论开始把重点从“模型强不强”转到“为什么先只给少数人用”。",
            "audience": "关注前沿模型发布策略和安全边界的 AI 从业者",
            "why_now": "大家已经不只在猜新模型多强，而是在拆厂商为什么先关着发。",
            "preview_quote_permalink": "https://www.reddit.com/r/artificial/comments/up123/q1",
            "detail": {
                "pain_point": "先小范围放量，暴露的是厂商对滥用和风控的担心。",
                "target_user_and_scene": "在看模型发布策略和安全边界变化的 AI 团队。",
                "why_test_now": "讨论开始从性能转到风险边界。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "如果更多厂商重复这种放量方式，就继续盯。",
                "stop_signal": "如果后续只剩性能讨论，就先放过。",
            },
        }
    ]

    def factory(model: str, timeout: float) -> _FakeClient:
        calls.append((model, timeout))
        return _FakeClient(payloads)

    await generate_card_content(draft, client_factory=factory)
    expected_timeout = float(load_card_content_rules()["timeouts"]["signal_seconds"])
    assert calls[0] == ("deepseek/deepseek-v4-flash", expected_timeout)


@pytest.mark.asyncio
async def test_generate_card_content_applies_category_winds_pack_rules() -> None:
    candidate = CandidatePack.model_validate(
        {
            **_candidate().model_dump(mode="json"),
            "candidate_id": "cand-category-001",
            "signal_id": "sig-category-001",
            "source_scope_id": "ecommerce-sellers",
            "source_scope_name": "电商与卖家",
            "topic_pack_id": "category-winds",
            "matched_subreddit": "EntrepreneurRideAlong",
            "title": "I've built in both a niche market (chess) and a brutally crowded one (SEO tools).",
            "matched_keywords": ["saturated niche amazon"],
            "top_communities": ["r/EntrepreneurRideAlong"],
            "intent_tags": ["趋势变化"],
            "evidence_quotes": [
                {
                    "text": "The co-founder move was the whole distribution strategy most people gloss over.",
                    "community": "r/EntrepreneurRideAlong",
                    "permalink": "https://www.reddit.com/r/EntrepreneurRideAlong/comments/cat123/q1",
                },
                {
                    "text": "The forgiveness margin concept is what keeps niche markets alive longer.",
                    "community": "r/EntrepreneurRideAlong",
                    "permalink": "https://www.reddit.com/r/EntrepreneurRideAlong/comments/cat123/q2",
                },
            ],
        }
    )
    draft = seed_validation_draft(candidate)
    client = _RecordingClient(
        [
            {
                "title": "做细分类目还是进红海，卖家开始重算有没有容错空间",
                "summary_line": "有人开始比较细分类目和红海类目，发现没有分发抓手和容错空间的方向很难撑住。",
                "audience": "在看新类目值不值得进场的卖家",
                "why_now": "讨论已经从聊经验，转到什么类目还有进场空间。",
                "preview_quote_permalink": "https://www.reddit.com/r/EntrepreneurRideAlong/comments/cat123/q1",
                "detail": {
                    "pain_point": "类目一挤，分发抓手和容错空间会先被压没。",
                    "target_user_and_scene": "在比较细分类目和红海类目时判断要不要进场。",
                    "why_test_now": "有人开始直接把分发抓手和容错空间摊出来比较。",
                    "min_test_action": "去看原始讨论",
                    "continue_signal": "继续看后面会不会有人继续拿分发抓手和容错空间做对比。",
                    "stop_signal": "如果后面没有新的类目对比，只剩抽象感想，就先别放大。",
                },
            }
        ]
    )
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: client
    )
    assert "容错空间" in result.title
    assert "红海" in result.summary_line
    assert "类目风向" in client.messages[0]["content"]
    assert "国际象棋" not in result.detail.pain_point
    assert "国际象棋" not in result.detail.pain_point
    assert "niche" not in result.detail.target_user_and_scene


@pytest.mark.asyncio
async def test_generate_card_content_applies_organic_discovery_pack_rules() -> None:
    candidate = _candidate().model_copy(
        update={
            "source_scope_id": "business-growth-ops",
            "source_scope_name": "商业增长与运营",
            "topic_pack_id": "organic-discovery",
            "matched_subreddit": "SEO",
            "title": "AI search ranking is changing",
            "matched_keywords": ["search visibility"],
            "top_communities": ["r/SEO"],
            "intent_tags": ["趋势变化"],
        }
    )
    draft = seed_validation_draft(candidate)
    draft = draft.model_copy(
        update={
            "evidence_quotes": [
                QuotePreview(
                    text="for SEO the big question is whether they’re weighting clean + trusted + easy to extract above traditional relevance",
                    community="r/SEO",
                    permalink="https://www.reddit.com/r/SEO/comments/extract/test1",
                ),
                QuotePreview(
                    text="sites may lose visibility just because their content is harder for these systems to parse cleanly",
                    community="r/SEO",
                    permalink="https://www.reddit.com/r/SEO/comments/extract/test2",
                ),
            ],
            "intent_tags": ["趋势变化"],
            "source_communities": ["r/SEO"],
        }
    )
    payloads = [
        {
            "title": "Claude代码泄露后SEO担心排名优先干净可信易提取内容",
            "summary_line": "论坛里有人在讨论 AI 搜索会不会偏爱更干净更容易提取的内容。",
            "audience": "SEO 从业者",
            "why_now": "论坛里开始有人在聊这个变化。",
            "preview_quote_permalink": "https://www.reddit.com/r/SEO/comments/extract/test1",
            "detail": {
                "pain_point": "pain",
                "target_user_and_scene": "scene",
                "why_test_now": "原话在问 AI 搜索会不会偏爱更干净、更容易提取的内容，r/SEO 这类页面可能要重新看内容结构。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "continue",
                "stop_signal": "stop",
            },
        }
    ]
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
    )
    assert "易提取" in result.title
    assert "容易提取" in result.summary_line
    assert "r/SEO" in result.detail.why_test_now
    assert "容易提取" in result.detail.why_test_now


@pytest.mark.asyncio
async def test_generate_card_content_upgrades_to_breakdown_card_when_evidence_is_strong() -> None:
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    payloads = [
        {
            "title": "销售团队在吵：每天都在给 CRM 补作业",
            "summary_line": "r/sales 有人说“我每天要花 30 分钟喂 Salesforce 数据”。这一周里，多个帖子都在讲回填负担。",
            "audience": "5-50 人团队里每天要回填 CRM 的一线销售",
            "why_now": "本周 r/sales 和 r/startups 都有类似帖子，讨论已经明确出现替代意图。",
            "preview_quote_permalink": "https://www.reddit.com/r/sales/comments/abc123/q1",
            "detail": {
                "pain_point": "表面在抱怨录入，底下是在抱怨时间被系统吃掉。",
                "target_user_and_scene": "一线销售在推进客户同时还得回填 CRM 的场景。",
                "why_test_now": "多帖、多社区都在重复这类负担，已经不是孤例。",
                "min_test_action": "去看原始讨论",
                "continue_signal": "如果后续继续出现替代询问和流程减负诉求，值得继续追。",
                "stop_signal": "如果后续只有单点吐槽，没有更多具体场景，就先别上升。",
            },
        },
        {
            "title": "大家骂的是 CRM，真正烦的是替流程背责任",
            "summary_line": "表面看是在嫌 CRM 重，真正反复暴露的是：销售不觉得这一步在帮自己赢单，只觉得在替流程背责任。",
            "thesis": "表面在骂录入麻烦，真正卡点是销售不认这一步的价值，只把它当成替管理层做合规记录。",
            "writing_angle_or_perspective": "从“工具不好用”切到“责任感不归属”这个角度看，会比讲功能更准。",
            "tension_point_or_why_it_matters": "如果你只盯着简化字段，会误以为这是 UI 问题；原话真正指向的是角色关系出了问题。",
            "title_hooks": ["不是 CRM 太重，是销售根本不认这一步算自己的工作"],
            "quote_pack": [
                "I spend 30 min a day feeding Salesforce data.｜我每天要花 30 分钟喂 Salesforce 数据。｜r/sales",
                "CRM updates feel like admin work for my manager, not me.｜CRM 更新像是在替经理做行政活，不像在帮我。｜r/startups",
            ],
            "supporting_quote_permalinks": [
                "https://www.reddit.com/r/sales/comments/abc123/q1",
                "https://www.reddit.com/r/startups/comments/def456/q2",
            ],
        },
    ]
    result = await generate_card_content(
        draft, client_factory=lambda _model, _timeout: _FakeClient(payloads)
    )
    assert result.card_type == "write"
    assert result.lane == "breakdown"
    assert result.detail.thesis.startswith("表面在骂录入麻烦")
    assert (
        result.evidence_quotes[0].permalink
        == "https://www.reddit.com/r/sales/comments/abc123/q1"
    )
    assert result.audience == "5-50 人团队里每天要回填 CRM 的一线销售"
    assert "switch_signal_7d" not in result.why_now
    assert "意图" not in result.why_now
    assert result.why_now == "本周 r/sales 和 r/startups 都有类似帖子，讨论已经明确出现替代。"


def test_should_be_breakdown_accepts_single_community_when_threads_repeat() -> None:
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=1))
    draft = draft.model_copy(
        update={
            "evidence_quotes": [
                QuotePreview(text="one", community="r/sales", permalink="1"),
                QuotePreview(text="two", community="r/sales", permalink="2"),
                QuotePreview(text="three", community="r/sales", permalink="3"),
            ]
        }
    )
    assert should_be_breakdown(
        draft,
        {
            "thesis": "真正卡点不是工具，而是责任不归属。",
            "quote_pack": ["a｜一｜r/sales", "b｜二｜r/sales"],
            "supporting_quote_permalinks": ["1", "2"],
        },
    )


def test_should_be_breakdown_rejects_signal_rehash_thesis() -> None:
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    draft = draft.model_copy(
        update={
            "summary_line": "大家开始意识到 CRM 真正让人烦的不是录入动作，而是像在替经理补记录。",
            "why_now": "这周两边都把抱怨指向了同一个问题：这一步根本不被当成自己的工作。",
            "evidence_quotes": [
                QuotePreview(text="one", community="r/sales", permalink="1"),
                QuotePreview(text="two", community="r/startups", permalink="2"),
                QuotePreview(text="three", community="r/revops", permalink="3"),
            ],
        }
    )
    assert not should_be_breakdown(
        draft,
        {
            "title": "CRM 真正让人烦的，是像在替经理补记录",
            "summary_line": "大家开始意识到 CRM 真正让人烦的不是录入动作，而是像在替经理补记录。",
            "why_now": "这周两边都把抱怨指向了同一个问题：这一步根本不被当成自己的工作。",
            "thesis": "大家开始意识到 CRM 真正让人烦的不是录入动作，而是像在替经理补记录。",
            "quote_pack": [
                "one｜一｜r/sales",
                "two｜二｜r/startups",
            ],
            "supporting_quote_permalinks": ["1", "2"],
        },
    )


def test_should_be_breakdown_rejects_invalid_supporting_quotes() -> None:
    draft = seed_validation_draft(_candidate(thread_count=3, community_count=2))
    draft = draft.model_copy(
        update={
            "evidence_quotes": [
                QuotePreview(text="one", community="r/sales", permalink="1"),
                QuotePreview(text="two", community="r/startups", permalink="2"),
                QuotePreview(text="three", community="r/revops", permalink="3"),
            ]
        }
    )
    assert not should_be_breakdown(
        draft,
        {
            "title": "销售不是烦 CRM 重，而是不认这一步算自己的工作",
            "summary_line": "表面在骂工具，真正暴露的是责任不归属。",
            "why_now": "两边都把抱怨从工具重，推到了“这活到底算谁的”。",
            "thesis": "销售抗拒 CRM，不只是嫌麻烦，而是不认这一步算自己的工作。",
            "quote_pack": [
                "one｜一｜r/sales",
                "two｜二｜r/startups",
            ],
            "supporting_quote_permalinks": ["1", "missing"],
        },
    )


def test_build_signal_why_now_turns_internal_tags_into_human_copy() -> None:
    why_now = build_signal_why_now(
        source_communities=["r/sales", "r/revops"],
        thread_count=3,
        community_count=2,
        intent_tags=["求替代", "明确阻塞 / 吐槽到影响行动"],
        why_now_reason="switch_signal_7d",
    )
    assert "switch_signal_7d" not in why_now
    assert "意图" not in why_now
    assert "r/sales、r/revops" in why_now
    assert "3 条讨论" in why_now
    assert "找替代" in why_now


def test_build_signal_why_now_supports_newer_intent_taxonomy() -> None:
    why_now = build_signal_why_now(
        source_communities=["r/artificial"],
        thread_count=2,
        community_count=1,
        intent_tags=["值得写", "先看权限和追责"],
        why_now_reason="recurring_7d",
    )
    assert "这已经不只是顺手一吐槽" in why_now
    assert "权限和追责" in why_now


def test_build_signal_why_now_does_not_claim_repeated_pattern_for_single_thread() -> (
    None
):
    why_now = build_signal_why_now(
        source_communities=["r/cursor"],
        thread_count=1,
        community_count=1,
        intent_tags=["趋势变化"],
        why_now_reason="recurring_7d",
    )
    why_test_now = build_signal_why_test_now(
        source_communities=["r/cursor"],
        thread_count=1,
        community_count=1,
        intent_tags=["趋势变化"],
        why_now_reason="recurring_7d",
    )

    assert "1个帖子" not in why_now
    assert "反复" not in why_now
    assert "反复出现" not in why_now
    assert "反复出现" not in why_test_now
    assert "真实取舍" in why_now
    assert "还值不值" in why_now
    assert "这条原话" in why_test_now


def test_polish_published_card_preserves_new_signal_semantics_by_default() -> None:
    card = {
        "card_id": "clue-crm-data-entry-drag",
        "card_type": "validate",
        "title": "CRM录入的阻力不是技术问题，是销售团队的‘心理摩擦力’",
        "summary_line": "这迫使他们不得不去做额外确认。",
        "audience": "r/sales销售人员",
        "why_now": "销售开始重新判断 CRM 回填值不值，因为这会直接影响团队要不要继续忍受手工录入。",
        "why_now_reason": "switch_signal_7d",
        "signal_level": "rising",
        "intent_tags": ["求替代", "明确阻塞 / 吐槽到影响行动"],
        "thread_count": 3,
        "community_count": 2,
        "source_module": {"primary_communities": ["r/sales", "r/revops"]},
        "detail": {
            "pain_point": "销售不是不会用 CRM，而是不想每天替系统补数据。",
            "target_user_and_scene": "每天跑客户、晚上还要补 CRM 的销售。",
            "why_test_now": "原话里说 feeding Salesforce data，说明卡点不是功能缺失，而是录入这一步没人愿意接。",
            "min_test_action": "去看原始讨论",
            "continue_signal": "继续看 Salesforce data、admin work、lighter alternatives 这些词会不会继续出现。",
            "stop_signal": "如果后面只是在聊 CRM 教程，没有继续提录入负担和替代工具，就不用放大。",
        },
    }
    polished = polish_published_card(card)

    assert polished["why_now"] == card["why_now"]
    assert polished["detail"]["why_test_now"] == card["detail"]["why_test_now"]
    assert polished["detail"]["continue_signal"] == card["detail"]["continue_signal"]
    assert polished["detail"]["stop_signal"] == card["detail"]["stop_signal"]


def test_polish_published_card_can_rewrite_legacy_cards_when_requested() -> None:
    polished = polish_published_card(
        {
            "card_id": "clue-crm-data-entry-drag",
            "card_type": "write",
            "title": "CRM录入的阻力不是技术问题，是销售团队的‘心理摩擦力’",
            "summary_line": "这迫使他们不得不去做额外确认。",
            "audience": "r/sales销售人员",
            "why_now": "r/sales 3帖2社区，switch_signal_7d意图求替代明确阻塞温度rising",
            "why_now_reason": "switch_signal_7d",
            "signal_level": "rising",
            "intent_tags": ["求替代", "明确阻塞 / 吐槽到影响行动"],
            "thread_count": 3,
            "community_count": 2,
            "source_module": {"primary_communities": ["r/sales", "r/revops"]},
            "detail": {
                "thesis": "CRM系统采纳的核心障碍并非功能设计，而是销售团队在重复性数据录入任务中产生的‘心理摩擦力’。",
                "writing_angle_or_perspective": "从反直觉工作流切入。",
                "tension_point_or_why_it_matters": "这暴露了根本矛盾。",
                "title_hooks": ["你的CRM数据正在被销售团队的‘心理摩擦力’悄悄腐蚀"],
                "quote_pack": [],
            },
        },
        preserve_semantic_fields=False,
    )
    assert polished["title"].startswith("销售不爱回填 CRM")
    assert "心理摩擦力" not in polished["detail"]["thesis"]
    assert "根本矛盾" not in polished["detail"]["tension_point_or_why_it_matters"]
    assert "switch_signal_7d" not in polished["why_now"]


def test_polish_published_card_rewrites_audience_out_of_subreddit_listing() -> None:
    polished = polish_published_card(
        {
            "card_id": "clue-support-kb-answer-gap",
            "card_type": "write",
            "title": "知识库搜出的是半成品",
            "summary_line": "客服觉得搜出来的答案不能直接回。",
            "audience": "r/customersupport、r/helpdesk 和 r/sysadmin 的客服与 IT 支持人员在工单处理场景下抱怨知识库问题",
            "why_now": "r/helpdesk 2帖1社区 recurring_7d",
            "why_now_reason": "recurring_7d",
            "signal_level": "rising",
            "intent_tags": ["求推荐 / 求解法", "明确阻塞 / 吐槽到影响行动"],
            "thread_count": 2,
            "community_count": 1,
            "source_module": {"primary_communities": ["r/helpdesk"]},
            "detail": {
                "thesis": "客服和 IT 支持人员搜到的不是能直接回给用户的答案。",
                "writing_angle_or_perspective": "从工单处理切入。",
                "tension_point_or_why_it_matters": "这会拖慢回复。",
                "title_hooks": [],
                "quote_pack": [],
            },
        },
        preserve_semantic_fields=False,
    )
    assert "r/" not in polished["audience"]
    assert "客服与 IT 支持人员" in polished["audience"]
