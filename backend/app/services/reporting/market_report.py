from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

from app.services.reporting.gtm_planner import GTMActionPlanner, GTMPlan
from app.services.analysis.persona_generator import PersonaResult
from app.services.analysis.quote_extractor import QuoteResult
from app.services.analysis.saturation_matrix import BrandSaturation, CommunitySaturation
from app.services.llm.marketing_copy import CopyAmmo


class MarketReportBuilder:
    """Builds a market-oriented report context for template rendering.

    This class provides quick rule-based fallbacks to allow graceful
    degradation when LLMs are disabled.
    """

    def _build_metric_cards(self, analysis: Mapping[str, object]) -> Dict[str, str]:
        insights = analysis.get("insights") or {}
        sources = analysis.get("sources") or {}
        posts = int((sources or {}).get("posts_analyzed") or 0)
        communities = list((sources or {}).get("communities") or [])
        comps = list((insights or {}).get("competitors") or [])
        pains = list((insights or {}).get("pain_points") or [])
        return {
            "card_posts": str(posts),
            "card_communities": str(len(communities)),
            "card_competitors": str(len(comps)),
            "card_pains": str(len(pains)),
        }

    def _persona_summary(self, personas: Sequence[PersonaResult]) -> str:
        if not personas:
            return "暂无画像"
        items = [f"{p.community}: {p.persona_label} ({p.confidence:.0%})" for p in personas]
        return ", ".join(items)

    def _quotes_top(self, quotes: Sequence[QuoteResult]) -> str:
        if not quotes:
            return "无典型引言"
        return f"{quotes[0].text} —— 来自 {quotes[0].source}"

    def _saturation_summary(self, saturation: Sequence[CommunitySaturation]) -> str:
        if not saturation:
            return "未计算饱和度"
        parts: List[str] = []
        for s in saturation[:3]:
            parts.append(f"{s.community} 总体饱和度 {s.overall_saturation:.0%}")
        return ", ".join(parts)

    def build_context(
        self,
        *,
        analysis: Mapping[str, object],
        personas: List[PersonaResult],
        quotes: List[QuoteResult],
        saturation: List[CommunitySaturation],
        copy_ammo: Dict[str, CopyAmmo],
        gtm_plans: Dict[str, GTMPlan],
    ) -> Dict[str, str]:
        ctx: Dict[str, str] = {
            "title": "市场洞察报告 v1",
        }
        ctx.update(self._build_metric_cards(analysis))
        ctx["persona_list"] = self._persona_summary(personas)
        ctx["top_quote"] = self._quotes_top(quotes)
        ctx["saturation_summary"] = self._saturation_summary(saturation)
        # 简单GTМ摘要：列出计划覆盖的机会数
        ctx["gtm_summary"] = f"{len(gtm_plans)} 个机会已生成GTM行动计划"
        return ctx

    # ---------- Quick fallbacks from analysis (Phase 1 parallel outputs) ----------
    async def quick_personas(self, analysis: Mapping[str, object]) -> List[PersonaResult]:
        sources = analysis.get("sources") or {}
        communities = list((sources or {}).get("communities") or [])
        if communities:
            community = str(communities[0])
        else:
            community = "r/unknown"
        return [
            PersonaResult(
                community=community,
                persona_label="DIY用户",
                traits=["在乎性价比", "反订阅费"],
                strategy="痛点切入",
                confidence=0.7,
                method="rules",
            )
        ]

    async def quick_quotes(self, analysis: Mapping[str, object]) -> List[QuoteResult]:
        insights = analysis.get("insights") or {}
        pains = list((insights or {}).get("pain_points") or [])
        desc = str((pains[0] or {}).get("description") or "订阅费太贵了") if pains else "订阅费太贵了"
        src = str(((analysis.get("sources") or {}).get("communities") or ["r/unknown"])[0])
        return [
            QuoteResult(
                pain_description=desc,
                user_voice="硬件已经很贵，为什么还要每月付费？",
                source_community=src,
                sentiment_score=-0.6,
                confidence=0.6,
            )
        ]

    async def quick_saturation(self, analysis: Mapping[str, object]) -> List[CommunitySaturation]:
        sources = analysis.get("sources") or {}
        communities = list((sources or {}).get("communities") or [])
        community = str(communities[0]) if communities else "r/unknown"
        return [
            CommunitySaturation(
                community=community,
                brands=[BrandSaturation(brand="GenericBrand", saturation=0.5, status="中等")],
                overall_saturation=0.5,
            )
        ]

    def quick_copy_ammo(self, analysis: Mapping[str, object]) -> Dict[str, CopyAmmo]:
        insights = analysis.get("insights") or {}
        oppty = list((insights or {}).get("action_items") or [])
        if not oppty:
            return {}
        key = str((oppty[0] or {}).get("id") or "oppty-1")
        return {
            key: CopyAmmo(
                vs_subscription="每年多花$XXX并不值得",
                vs_competitor="",
                pain_resonance="我们受够了订阅费陷阱，所以做了这款产品",
                value_prop="一次性买断，持续升级",
            )
        }

    def quick_gtm_plans(
        self,
        *,
        analysis: Mapping[str, object],
        personas: Sequence[PersonaResult],
    ) -> Dict[str, GTMPlan]:
        insights = analysis.get("insights") or {}
        oppty = list((insights or {}).get("action_items") or [])
        if not oppty or not personas:
            return {}
        planner = GTMActionPlanner()
        first = oppty[0]
        plan = planner.generate(
            opportunity=dict(first),  # shallow copy ok for tests
            persona=personas[0],
            moderation_score=0.5,
        )
        key = str((first or {}).get("id") or "oppty-1")
        return {key: plan}


__all__ = [
    "PersonaResult",
    "QuoteResult",
    "BrandSaturation",
    "CommunitySaturation",
    "CopyAmmo",
    "MarketReportBuilder",
]
