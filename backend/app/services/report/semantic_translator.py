from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PsRatioCopy:
    ratio_text: str
    conclusion: str
    interpretation: str
    health_assessment: str


@dataclass(frozen=True)
class CompetitionCopy:
    level: str
    interpretation: str


def build_ps_ratio_copy(
    ps_ratio_value:Optional[ float],
    *,
    report_tier: str,
    is_estimated: bool = False,
) -> PsRatioCopy:
    ratio_text = f"{ps_ratio_value:.2f}" if isinstance(ps_ratio_value, (int, float)) else "N/A"
    estimate_note = "基于当前讨论强度判断。" if is_estimated else ""

    if report_tier == "X_blocked":
        return PsRatioCopy(
            ratio_text=ratio_text,
            conclusion="供需关系还没看清，先别急着拍板。",
            interpretation="这批讨论更适合当雷达线索，先补够样本再判断是真需求还是偶发噪音。",
            health_assessment="进场信号：继续观察",
        )

    if ps_ratio_value is None:
        return PsRatioCopy(
            ratio_text=ratio_text,
            conclusion="供需关系暂时还不够清晰。",
            interpretation="现阶段先盯住重复抱怨和高频场景，等更多样本出来再决定切哪一刀。",
            health_assessment="进场信号：继续观察",
        )

    if ps_ratio_value <= 0.2:
        return PsRatioCopy(
            ratio_text=ratio_text,
            conclusion="供需缺口明显，抱怨多，但像样解法还不够多。",
            interpretation=f"现在更像痛点积压期，谁先把核心麻烦讲清并做顺，谁更容易抢到第一波心智。{estimate_note}".strip(),
            health_assessment="进场信号：强烈建议",
        )
    if ps_ratio_value < 0.8:
        return PsRatioCopy(
            ratio_text=ratio_text,
            conclusion="用户问题还在持续冒头，成熟方案还没把需求吃干净。",
            interpretation=f"这说明市场还留着可切的空位，适合围绕高频麻烦做更省心的一步式方案。{estimate_note}".strip(),
            health_assessment="进场信号：建议推进",
        )
    if ps_ratio_value <= 1.2:
        return PsRatioCopy(
            ratio_text=ratio_text,
            conclusion="供需两端已经开始接近平衡，市场不算空白，但也没到无缝可钻。",
            interpretation=f"现在拼的不是有没有产品，而是谁把体验、效率和信任做得更顺手。{estimate_note}".strip(),
            health_assessment="进场信号：谨慎推进",
        )
    return PsRatioCopy(
        ratio_text=ratio_text,
        conclusion="赛道里已经有不少成熟解法，单靠功能堆料很难打动人。",
        interpretation=f"这更像方案成熟期，想切进去要找更细的场景，或者把体验做出明显差距。{estimate_note}".strip(),
        health_assessment="进场信号：细分切入",
    )


def build_competition_copy(report_tier: str, community_count: int) -> CompetitionCopy:
    if report_tier == "X_blocked":
        return CompetitionCopy(
            level="样本偏轻，暂不下竞争结论",
            interpretation="现在先把高频场景和重复抱怨找准，比急着判断竞争激烈不激烈更重要。",
        )
    if report_tier == "A_full":
        return CompetitionCopy(
            level="竞争可见，但仍有结构性机会",
            interpretation=(
                "这不是没人做，而是老解法还没把用户抱怨吃干净。"
                if community_count >= 3
                else "讨论已经开始集中，说明市场有认知基础，但体验层面还留着切入口。"
            ),
        )
    if report_tier == "B_trimmed":
        return CompetitionCopy(
            level="方向成立，值得继续看竞争空位",
            interpretation="现在已经能看出主要玩家和常见套路，下一步该盯差异化而不是盲目跟做。",
        )
    return CompetitionCopy(
        level="市场刚冒头，先看需求聚不聚",
        interpretation="现阶段更重要的是确认需求是不是持续出现，而不是过早给竞争下死结论。",
    )
