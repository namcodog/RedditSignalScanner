from __future__ import annotations

from app.services.report.gtm_planner import GTMActionPlanner
from app.services.report.market_report import PersonaResult


def test_gtm_planner_fallback_generates_actions() -> None:
    planner = GTMActionPlanner()
    persona = PersonaResult(
        community="r/startups",
        persona_label="DIY用户",
        traits=["在乎性价比", "反订阅费"],
        strategy="痛点切入",
        confidence=0.7,
        method="rules",
    )
    opportunity = {
        "id": "oppty-1",
        "problem_definition": "订阅费陷阱",
    }

    plan = planner.generate(opportunity=opportunity, persona=persona, moderation_score=0.4)

    assert plan.opportunity_id == "oppty-1"
    assert plan.target_community == "r/startups"
    assert len(plan.actions) >= 3
    # 基本相位与中文字段存在
    phases = {a.phase for a in plan.actions}
    assert any("W1 - 潜伏" in p for p in phases)


def test_gtm_planner_generates_two_weeks_min_actions_count() -> None:
    planner = GTMActionPlanner()
    persona = PersonaResult(
        community="r/startups",
        persona_label="DIY用户",
        traits=["在乎性价比", "反订阅费"],
        strategy="痛点切入",
        confidence=0.7,
        method="rules",
    )
    opportunity = {
        "id": "oppty-2",
        "problem_definition": "订阅费陷阱",
    }

    plan = planner.generate(opportunity=opportunity, persona=persona, moderation_score=0.3)
    assert len(plan.actions) >= 6  # 两周最小 6 条
    labels = {a.phase for a in plan.actions}
    assert any("W1 - 潜伏" in p for p in labels)
    assert any("W2 - 软植入" in p for p in labels)


def test_gtm_planner_compliance_warning_and_copy_tone() -> None:
    planner = GTMActionPlanner()
    persona = PersonaResult(
        community="r/startups",
        persona_label="DIY用户",
        traits=["在乎性价比", "反订阅费"],
        strategy="痛点切入",
        confidence=0.7,
        method="rules",
    )
    opportunity = {
        "id": "oppty-3",
        "problem_definition": "订阅费陷阱",
    }
    plan = planner.generate(opportunity=opportunity, persona=persona, moderation_score=0.95)
    # 合规提示存在
    assert plan.compliance_warning is not None
    # 高审核强度时，不应出现“发布帖子”的直接用语
    assert all("发布帖子" not in a.action for a in plan.actions)


def test_gtm_planner_traits_customize_actions() -> None:
    planner = GTMActionPlanner()
    persona = PersonaResult(
        community="r/startups",
        persona_label="反订阅派",
        traits=["反订阅", "在乎价格"],
        strategy="痛点切入",
        confidence=0.7,
        method="rules",
    )
    opportunity = {"id": "oppty-4", "problem_definition": "订阅费陷阱"}
    plan = planner.generate(opportunity=opportunity, persona=persona, moderation_score=0.4)
    # 至少一条行动包含“聚焦：反订阅”或“强调性价比”字样
    joined = "\n".join(a.action for a in plan.actions)
    assert ("聚焦：反订阅" in joined) or ("强调性价比" in joined)
