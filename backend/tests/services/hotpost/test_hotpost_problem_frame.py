from app.services.hotpost.problem_frame import build_hotpost_problem_frame
from app.services.hotpost.query_resolver import HotpostQueryResolution


def test_build_problem_frame_classifies_generic_complaint_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="大家最常吐槽咖啡机什么？",
            search_query="coffee machine maintenance complaints",
            keywords=["coffee", "machine", "maintenance"],
            subreddits=["r/coffee"],
            source="llm",
        ),
        core_terms=["coffee", "machine", "maintenance"],
    )

    assert frame.query_family == "generic_complaint_discovery"
    assert frame.primary_friction == "trust_gap"
    assert "maintenance" in frame.forbidden_narrowing_terms
    assert frame.retrieval_hypotheses[0] == "coffee machine complaints"


def test_build_problem_frame_classifies_english_generic_complaint_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="what do people complain most about coffee machines?",
            search_query="what do people complain most about coffee machines?",
            keywords=["coffee", "machine"],
            subreddits=["r/coffee"],
            source="original",
        ),
        core_terms=["coffee", "machine"],
    )

    assert frame.query_family == "generic_complaint_discovery"
    assert frame.primary_friction == "trust_gap"
    assert frame.retrieval_hypotheses[0] == "coffee machine complaints"


def test_build_problem_frame_keeps_specific_issue_anchor_for_generic_complaint_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why users complain adobe premiere keeps crashing after updates",
            search_query="why users complain adobe premiere keeps crashing after updates",
            keywords=["users", "complain", "adobe", "premiere", "crashing", "updates"],
            subreddits=["r/adobe"],
            source="original",
        ),
        core_terms=["users", "complain", "adobe", "premiere", "crashing", "updates"],
    )

    assert frame.query_family == "generic_complaint_discovery"
    assert frame.retrieval_hypotheses[0] == "why users complain adobe premiere keeps crashing after updates"
    assert any("adobe premiere complaints" in query for query in frame.retrieval_hypotheses)


def test_build_problem_frame_classifies_comparison_complaint_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="codex vs claude instruction following complaints",
            search_query="codex vs claude instruction following complaints",
            keywords=["codex", "claude", "comparison", "complaints"],
            subreddits=["r/openai"],
            source="original",
        ),
        core_terms=["codex", "claude", "comparison", "complaints"],
    )

    assert frame.query_family == "comparison_complaint_discovery"
    assert frame.retrieval_hypotheses[0] == "codex vs claude complaints"
    assert "codex complaints" in frame.retrieval_hypotheses
    assert "claude complaints" in frame.retrieval_hypotheses


def test_build_problem_frame_classifies_chinese_comparison_complaint_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么大家说 Codex 比 Claude 更能听懂指令",
            search_query="why codex is better than claude for instruction following",
            keywords=["codex", "claude", "instruction", "following"],
            subreddits=[],
            source="fallback",
        ),
        core_terms=["codex", "claude", "instruction", "following"],
    )

    assert frame.query_family == "comparison_complaint_discovery"
    assert "codex complaints" in frame.retrieval_hypotheses
    assert "claude complaints" in frame.retrieval_hypotheses


def test_build_problem_frame_classifies_chinese_compare_query_with_xiangbi_cue() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="AI coding 里，Codex 和 Claude 相比，大家为什么更偏向 Codex？",
            search_query="why developers prefer codex over claude in ai coding",
            keywords=["codex", "claude", "ai coding", "prefer"],
            subreddits=[],
            source="llm",
        ),
        core_terms=["codex", "claude", "coding", "prefer"],
    )

    assert frame.query_family == "comparison_complaint_discovery"
    assert "codex complaints" in frame.retrieval_hypotheses
    assert "claude complaints" in frame.retrieval_hypotheses


def test_build_problem_frame_classifies_conversion_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么TikTok内容有曝光却还是卖不出去？",
            search_query="tiktok no purchase conversion",
            keywords=["tiktok", "traffic", "purchase", "conversion"],
            subreddits=["r/tiktokads"],
            source="llm",
        ),
        core_terms=["tiktok", "traffic", "purchase", "conversion"],
    )

    assert frame.query_family == "platform_conversion_friction"
    assert frame.primary_friction == "weak_buy_reason"
    assert frame.object_terms[:2] == ["tiktok", "traffic"]
    assert "transaction_friction" not in frame.secondary_frictions
    assert "tiktok ads no sales" in frame.retrieval_hypotheses
    assert "tiktok seller no orders" in frame.retrieval_hypotheses


def test_build_problem_frame_ignores_english_glue_terms_in_conversion_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么tiktok上做的内容有流量但却没有转化购买?",
            search_query="Why TikTok content gets traffic but no purchase conversions",
            keywords=["tiktok", "traffic", "conversion", "purchase"],
            subreddits=["r/tiktok"],
            source="llm",
        ),
        core_terms=["tiktok", "traffic", "conversion", "purchase"],
    )

    assert "why" not in frame.object_terms
    assert "gets" not in frame.object_terms
    assert frame.query_family == "platform_conversion_friction"
    assert frame.retrieval_hypotheses[0] == "tiktok ads no sales"


def test_build_problem_frame_frontloads_pre_purchase_hypotheses_for_platform_conversion() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why do tiktok ads get clicks but still no sales?",
            search_query="why do tiktok ads get clicks but still no sales?",
            keywords=["tiktok", "ads", "clicks", "sales"],
            subreddits=["r/tiktokads"],
            source="original",
        ),
        core_terms=["tiktok", "ads", "clicks", "sales"],
    )

    assert frame.query_family == "platform_conversion_friction"
    assert frame.retrieval_hypotheses[:3] == [
        "tiktok ads no sales",
        "tiktok ads tracking conversion",
        "tiktok ads checkout conversion",
    ]


def test_build_problem_frame_classifies_business_friction_query() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="卖成人用品时，最容易卡成交的地方是什么？",
            search_query="selling adult products conversion friction",
            keywords=["adult", "products", "sales", "conversion", "payment", "trust"],
            subreddits=["r/sextoys"],
            source="llm",
        ),
        core_terms=["adult", "products", "sales", "conversion", "payment", "trust"],
    )

    assert frame.query_family == "business_friction_discovery"
    assert frame.primary_friction == "transaction_friction"
    assert "trust_gap" in frame.secondary_frictions
    assert frame.retrieval_hypotheses[0] == "adult products sales business challenges"


def test_build_problem_frame_expands_specific_issue_hypotheses() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="why notion ai output is garbage and keeps rewriting my notes",
            search_query="why notion ai output is garbage and keeps rewriting my notes",
            keywords=["notion", "ai", "output", "garbage", "rewriting", "notes"],
            subreddits=[],
            source="original",
        ),
        core_terms=["notion", "ai", "output", "garbage", "rewriting", "notes"],
    )

    assert frame.query_family == "specific_issue"
    assert "notion ai output issue" in frame.retrieval_hypotheses
    assert "notion ai output complaints" in frame.retrieval_hypotheses


def test_build_problem_frame_uses_specific_issue_when_chinese_query_contains_explicit_symptom_hints() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="为什么很多人吐槽 Notion AI 会把会议纪要写成套话，还会漏掉 action items？",
            search_query="notion ai meeting notes vague misses action items",
            keywords=["notion", "meeting notes", "vague", "misses action items"],
            subreddits=["r/notion"],
            source="llm",
        ),
        core_terms=["notion", "ai", "meeting", "notes", "vague", "misses", "action", "items"],
    )

    assert frame.query_family == "specific_issue"


def test_build_problem_frame_does_not_misclassify_business_when_query_mentions_users() -> None:
    frame = build_hotpost_problem_frame(
        mode="rant",
        resolution=HotpostQueryResolution(
            original_query="Premiere Pro 26 导出时卡死/崩溃/绿屏，Reddit 用户具体在骂什么？",
            search_query="premiere pro 26 export freeze crash green screen complaints",
            keywords=["premiere", "export", "freeze", "crash", "green screen"],
            subreddits=["r/premiere"],
            source="llm",
        ),
        core_terms=["premiere", "export", "freeze", "crash", "green", "screen"],
    )

    assert frame.query_family == "specific_issue"
