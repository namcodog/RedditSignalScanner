from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass(slots=True)
class GTMAction:
    day: str
    phase: str
    action: str
    goal: str


@dataclass(slots=True)
class GTMPlan:
    opportunity_id: str
    target_community: str
    actions: List[GTMAction]
    compliance_warning: Optional[str] = None


PHASES_W1: Dict[str, Dict[str, str]] = {
    "lurk": {
        "day": "周一",
        "phase": "W1 - 潜伏",
        "template": "在 r/{community} {count}个抱怨'{keyword}'的帖子下回复，表达共情与求证",
        "goal": "建立可信度",
    },
    "value": {
        "day": "周二",
        "phase": "W1 - 价值",
        "template": "发布帖子：[讨论] 我受够了{keyword}，所以我整理了{solution_hint}",
        "goal": "成为话题引领者",
    },
    "discussion": {
        "day": "周四",
        "phase": "W1 - 讨论",
        "template": "在 r/{community} 发起征询：大家如何看待{keyword}？我收集到{solution_hint}",
        "goal": "扩大样本、验证共识",
    },
}

PHASES_W2: Dict[str, Dict[str, str]] = {
    "recap": {
        "day": "周一",
        "phase": "W2 - 复盘",
        "template": "复盘上周讨论要点，并补充3条新的证据源（不带外链）",
        "goal": "沉淀可信的知识",
    },
    "soft_pitch": {
        "day": "周三",
        "phase": "W2 - 软植入",
        "template": "在自己的帖子里自然提及解决思路：{solution_hint}",
        "goal": "测试市场反馈",
    },
    "ask_feedback": {
        "day": "周五",
        "phase": "W2 - 反馈",
        "template": "发起投票或征集用例：你们如何规避{keyword}？",
        "goal": "收集可操作反馈",
    },
}


class GTMActionPlanner:
    """Generate a lightweight 2-week Reddit GTM plan.

    LLM is optional. By default, uses template-based generation.
    """

    def __init__(self, llm_client: Optional["OpenAIChatClient"] = None) -> None:  # type: ignore[name-defined]
        self._llm = llm_client

    def generate(
        self,
        *,
        opportunity: Dict[str, object],
        persona: "PersonaResult",
        moderation_score: float,
    ) -> GTMPlan:
        community = persona.community or "unknown"
        # heuristics from opportunity
        keyword = str(
            opportunity.get("problem_definition")
            or opportunity.get("keyword")
            or "痛点"
        )
        solution_hint = str(
            opportunity.get("solution_hint") or "一份可执行的改进清单"
        )
        count = 3

        actions: List[GTMAction] = []

        # 优先尝试 LLM 生成（若提供了 llm_client），失败则回退模板
        if self._llm is not None:
            try:
                llm_actions = self._gen_llm_plan(
                    {
                        "community": community,
                        "keyword": keyword,
                        "solution_hint": solution_hint,
                        "count": count,
                    }
                )
                if llm_actions:
                    actions = llm_actions
            except Exception:
                actions = []

        def _emit(phases: Dict[str, Dict[str, str]]) -> None:
            for key in phases:
                spec = phases[key]
                txt = spec["template"].format(
                    community=community,
                    keyword=keyword,
                    solution_hint=solution_hint,
                    count=count,
                )
                # 基于 persona.traits 的轻量定制（不改变结构）
                try:
                    traits = []
                    if hasattr(persona, "traits"):
                        traits = list(getattr(persona, "traits") or [])  # type: ignore[assignment]
                    trait_text = " ".join(str(t) for t in traits)
                    if any(k in trait_text for k in ("反订阅", "订阅", "反订阅费")) and "订阅" not in txt:
                        txt += "（聚焦：反订阅）"
                    if any(k in trait_text for k in ("性价比", "价格")) and "价格" not in txt and "性价比" not in txt:
                        txt += "（强调性价比）"
                except Exception:
                    pass
                actions.append(
                    GTMAction(
                        day=spec["day"],
                        phase=spec["phase"],
                        action=txt,
                        goal=spec["goal"],
                    )
                )

        _emit(PHASES_W1)
        _emit(PHASES_W2)

        warning: Optional[str] = None
        if moderation_score >= 0.9:
            warning = "社区审核较严，请降低外链与品牌露出强度"
            # 高审核强度：避免“发布帖子”语气，替换为更保守的互动方式
            safe_actions: List[GTMAction] = []
            for a in actions:
                text = a.action.replace("发布帖子", "在热门贴下总结要点")
                text = text.replace("发起征询", "在置顶月报贴留言征询")
                safe_actions.append(GTMAction(day=a.day, phase=a.phase, action=text, goal=a.goal))
            actions = safe_actions

        return GTMPlan(
            opportunity_id=str(opportunity.get("id") or "oppty-1"),
            target_community=community,
            actions=actions,
            compliance_warning=warning,
        )

    # ----------------- LLM support -----------------
    def _gen_llm_plan(self, context: Dict[str, Any]) -> List[GTMAction]:
        """Use LLM to craft a 2-week Reddit GTM plan.

        Contract: expects self._llm to be an OpenAIChatClient-like with
        a private `_chat_completion(messages, ...)` method. Any error returns [].
        Output format (LLM): JSON list of objects: {day, phase, action, goal}.
        """
        llm = self._llm
        if llm is None:
            return []

        sys_prompt = (
            "你是资深Reddit增长教练。给出为期两周的行动清单，避免硬广，强调共情、复盘、软植入与征询。"
            "必须返回JSON数组，每个元素包含 day, phase, action, goal 字段（中文）。"
        )
        user_prompt = (
            f"目标社区: r/{context.get('community')}\n"
            f"核心痛点: {context.get('keyword')}\n"
            f"解决线索: {context.get('solution_hint')}\n"
            "请输出两周(>=6条)的行动，phase包含W1/W2。"
        )
        messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]
        try:
            # type: ignore[attr-defined]
            content: str = llm._chat_completion(messages, max_tokens=600, temperature=0.3)  # noqa: SLF001
        except Exception:
            return []
        try:
            import json

            data = json.loads((content or "").strip())
            out: List[GTMAction] = []
            for item in data:
                try:
                    out.append(
                        GTMAction(
                            day=str(item.get("day", "")),
                            phase=str(item.get("phase", "")),
                            action=str(item.get("action", "")),
                            goal=str(item.get("goal", "")),
                        )
                    )
                except Exception:
                    continue
            return out
        except Exception:
            return []


__all__ = ["GTMAction", "GTMPlan", "GTMActionPlanner"]
