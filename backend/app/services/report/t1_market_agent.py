from __future__ import annotations

import logging
from typing import Any

from app.services.llm.market_analyst import MarketAnalyst
from app.services.analysis.t1_clustering import T1ClusteringService
from app.services.analysis.t1_stats import T1StatsService

logger = logging.getLogger(__name__)


from dataclasses import dataclass


@dataclass
class ReportInputs:
    stats: dict[str, Any]
    clusters: list[dict[str, Any]]
    product_description: str


class T1MarketReportAgent:
    """
    Orchestrates the generation of the T1 Market Report (Seller-Centric).
    Structure: Decision -> Battlefields -> Pains & Drivers -> Opportunities.
    """

    def __init__(
        self,
        stats_service: T1StatsService,
        clustering_service: T1ClusteringService,
        analyst: MarketAnalyst,
    ):
        self.stats_service = stats_service
        self.clustering_service = clustering_service
        self.analyst = analyst

    async def render_async(
        self,
        product_description: str = "Cross-border E-commerce Insights",
        quality_level: str = "standard",
    ) -> str:
        """
        Main entry point to generate the full Markdown report.
        """
        logger.info(f"Starting T1 Report Generation ({quality_level})...")

        # 1. Fetch Data
        stats = await self.stats_service.get_overview_stats()
        pain_clusters = await self.clustering_service.cluster_pains(limit=3)
        
        top_keywords_str = ", ".join([kw for comm in stats.get("top_communities", []) for kw in comm.get("top_keywords", [])[:3]])

        # 2. Render Sections
        
        # A. Header
        report = self._render_header(stats, product_description)

        # B. Decision Card
        if quality_level == "premium":
            decision = await self.analyst.generate_strategic_overview(
                product_description, stats, top_keywords_str
            )
            report += self._render_decision_card(decision)
        
        # C. Strategic Battlefields
        report += await self._render_battlefields(stats, product_description, quality_level)

        # D. Pains & Drivers
        report += await self._render_pains_and_drivers(pain_clusters, product_description, quality_level)

        # E. Opportunity Cards
        report += await self._render_opportunities(pain_clusters, product_description, quality_level)

        # F. Summary
        if quality_level == "premium":
            summary = await self.analyst.generate_summary(report)
            report = f"# 📝 核心摘要 (Executive Summary)\n> {summary}\n\n" + report

        return report

    def _render_header(self, stats: dict[str, Any], product_name: str) -> str:
        return f"""# 📊 {product_name} 市场洞察报告

## 1. 数据概览
- **分析范围**: 覆盖 {stats.get('community_count')} 个活跃社区，基于过去12个月的 {stats.get('total_posts', 0):,} 帖子与 {stats.get('total_comments', 0):,} 评论。
- **分析视角**: 卖家实战视角 (选品/引流/服务)。

---
"""

    def _render_decision_card(self, decision: dict[str, Any]) -> str:
        stage = decision.get("market_stage", "N/A")
        comp = decision.get("competition_level", "N/A")
        verdict = decision.get("strategic_verdict", "N/A")
        ps_insight = decision.get("ps_interpretation", "N/A")
        battlefields = decision.get("core_battlefields", [])
        
        bf_list = "\n".join([f"  - {bf}" for bf in battlefields])

        return f"""## 2. 🚦 决策仪表盘

> **战略建议**: **{verdict}**

| 市场阶段 | 竞争难度 |
| :--- | :--- |
| **{stage}** | **{comp}** |

### 🧠 深度解读
- **供需关系 (P/S)**: {ps_insight}
- **流量洼地推荐**:
{bf_list}

---
"""

    async def _render_battlefields(
        self,
        stats: dict[str, Any],
        product_desc: str,
        quality: str,
    ) -> str:
        section = "## 3. ⚔️ 核心流量战场\n\n"
        top_communities = stats.get("top_communities", [])[:3]

        for comm in top_communities:
            name = comm["name"]
            if quality == "premium":
                keywords = ", ".join(comm.get("top_keywords", [])[:5])
                insight = await self.analyst.generate_persona(
                    product_desc, name, keywords, comm.get("sample_title", "")
                )
                
                role = insight.get("persona_role", "N/A")
                goal = insight.get("jtbd_goal", "N/A")
                pain_level = insight.get("pain_intensity", "N/A")
                strategy = insight.get("ops_strategy", "N/A")

                section += f"### 📍 {name} (活跃度: {comm['comments']})\n"
                section += f"- **👤 核心人群**: {role}\n"
                section += f"- **🏁 核心诉求**: {goal}\n"
                section += f"- **📣 引流策略**: {strategy}\n\n"
            else:
                section += f"### {name}\n- Keywords: {', '.join(comm.get('top_keywords', []))}\n\n"
        
        section += "---\n"
        return section

    async def _render_pains_and_drivers(
        self,
        clusters: list[dict[str, Any]],
        product_desc: str,
        quality: str,
    ) -> str:
        section = "## 4. 🧬 痛点与需求挖掘\n\n"
        
        for idx, cluster in enumerate(clusters, 1):
            topic = cluster["topic"]
            if quality == "premium":
                # Safe list comprehension for samples
                raw_samples = cluster.get("samples", [])
                if raw_samples:
                    raw_comments = "\n".join([f"- {c}" for c in raw_samples[:3]])
                else:
                    raw_comments = "无样本"
                
                insight = await self.analyst.refine_pain_point(
                    product_desc, topic, raw_comments
                )
                
                title = insight.get("commercial_title", topic)
                root = insight.get("root_cause", "N/A")
                voice = insight.get("user_voice", "N/A")
                impression = insight.get("data_impression", "N/A")
                driver = insight.get("driver_analysis", "N/A")
                feature = insight.get("feature_mapping", "N/A")
                
                cluster["_insight_cache"] = insight

                section += f"### 🔸 痛点 {idx}: {title}\n"
                section += f"> *\"{voice}\"*\n\n"
                section += f"- **🔍 根因 (Why)**: {root}\n"
                section += f"- **📊 市场情绪**: {impression}\n"
                section += f"- **🚀 购买驱动力**: {driver}\n"
                section += f"- **🛠 潜在需求**: {feature}\n\n"
            else:
                section += f"### Pain {idx}: {topic}\n\n"
        
        section += "---\n"
        return section

    async def _render_opportunities(
        self,
        clusters: list[dict[str, Any]],
        product_desc: str,
        quality: str,
    ) -> str:
        section = "## 5. 💎 商业机会卡 (Business Opportunities)\n\n"
        
        if quality != "premium":
            return section

        for idx, cluster in enumerate(clusters, 1):
            cached = cluster.get("_insight_cache", {})
            pain_title = cached.get("commercial_title", cluster["topic"])
            pain_root = cached.get("root_cause", "")
            pain_insight = f"Driver: {cached.get('driver_analysis', '')}"
            
            opp = await self.analyst.generate_opportunity(
                product_desc, "Target Sellers", pain_title, pain_insight, pain_root
            )
            
            concept = opp.get("opportunity_concept", "N/A")
            vp = opp.get("value_prop", "N/A")
            
            # Handle actionable_steps list safely
            steps_list = opp.get("actionable_steps", [])
            if isinstance(steps_list, list):
                steps = ", ".join(steps_list)
            else:
                steps = str(steps_list)
                
            diff = opp.get("differentiation", "N/A")
            money = opp.get("monetization", "N/A")

            section += f"### 🚀 商机 {idx}: {concept}\n"
            section += f"- **💡 价值主张**: {vp}\n"
            section += f"- **👣 落地第一步**: {steps}\n"
            section += f"- **🦄 护城河**: {diff}\n"
            section += f"- **💰 变现模式**: {money}\n\n"

        return section
