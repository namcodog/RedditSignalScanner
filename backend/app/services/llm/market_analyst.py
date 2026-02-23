from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from app.services.llm.clients.openai_client import OpenAIChatClient
from app.services.llm.prompts import (
    BATTLEFIELD_PROMPT_TEMPLATE,
    INSIGHT_MINER_PROMPT_TEMPLATE,
    OPPORTUNITY_PROMPT_TEMPLATE,
    STRATEGIST_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class MarketAnalyst:
    """
    Orchestrates LLM calls to generate market insights using the Whitepaper Grade prompts.
    Injects expert knowledge (Context) into prompts.
    """

    def __init__(self, client: OpenAIChatClient):
        self.client = client
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load expert knowledge from YAML configuration files."""
        self.pain_dictionary = {}
        self.community_profiles = {}

        try:
            # Load Pain Dictionary
            pain_dict_path = Path("backend/config/pain_dictionary.yaml")
            if pain_dict_path.exists():
                with open(pain_dict_path, "r", encoding="utf-8") as f:
                    self.pain_dictionary = yaml.safe_load(f) or {}
                logger.info(f"Loaded {len(self.pain_dictionary)} entries from pain_dictionary.")

            # Load Community Profiles
            profiles_path = Path("backend/config/seed_communities.json")
            if profiles_path.exists():
                with open(profiles_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("seed_communities", []):
                        name = item.get("name")
                        keywords = item.get("description_keywords", [])
                        if name:
                            # Normalize r/ prefix
                            norm_name = name.lower()
                            self.community_profiles[norm_name] = "; ".join(keywords)
                logger.info(f"Loaded {len(self.community_profiles)} community profiles.")

        except Exception as e:
            logger.warning(f"Failed to load knowledge base: {e}")

    def _get_community_context(self, subreddit: str) -> str:
        """Retrieve expert context for a subreddit."""
        norm_name = subreddit.lower()
        if not norm_name.startswith("r/"):
            norm_name = f"r/{norm_name}"
        return self.community_profiles.get(norm_name, "无特定背景信息")

    def _get_pain_context(self, topic_keywords: str) -> str:
        """Retrieve expert insight based on keywords."""
        context_parts = []
        topic_lower = topic_keywords.lower()
        
        for key, info in self.pain_dictionary.items():
            if key in topic_lower:
                insight = info.get("insight", "")
                opp = info.get("opportunity", "")
                context_parts.append(f"[{info.get('title_cn', key)}]: {insight} (建议方向: {opp})")
        
        if not context_parts:
            return "无特定专家解读"
        return "\n".join(context_parts)

    def _parse_json_response(self, response_text: str) -> dict[str, Any]:
        """Helper to reliably parse JSON from LLM response."""
        try:
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response_text[:100]}...")
            return {}

    async def _generate_text(self, prompt: str, json_mode: bool = False) -> str:
        """
        Internal wrapper to handle async generation calls safely.
        """
        fmt = {"type": "json_object"} if json_mode else None
        try:
            return await self.client.generate(prompt, response_format=fmt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return "{}" if json_mode else ""

    async def generate_strategic_overview(
        self, 
        product_description: str, 
        stats: dict[str, Any], 
        top_keywords: str
    ) -> dict[str, Any]:
        """Generate the strategic decision card."""
        
        top_communities = stats.get("top_communities", [])
        top_comm_str = ", ".join([f"{c['name']} ({c['comments']} comments)" for c in top_communities[:5]])

        prompt = STRATEGIST_PROMPT_TEMPLATE.format(
            product_description=product_description,
            community_count=stats.get("community_count", 0),
            total_volume=stats.get("total_posts", 0) + stats.get("total_comments", 0),
            ps_ratio=round(stats.get("ps_ratio", 0.0), 2),
            top_communities_list=top_comm_str,
            top_keywords=top_keywords,
        )
        
        response = await self._generate_text(prompt, json_mode=True)
        return self._parse_json_response(response)

    async def generate_persona(
        self, product_description: str, subreddit: str, top_keywords: str, sample_posts: str
    ) -> dict[str, Any]:
        """Generate user persona and strategy for a battlefield."""
        context = self._get_community_context(subreddit)
        
        prompt = BATTLEFIELD_PROMPT_TEMPLATE.format(
            product_description=product_description,
            subreddit=subreddit,
            community_context=context,
            top_keywords=top_keywords,
            sample_posts=sample_posts,
        )
        
        response = await self._generate_text(prompt, json_mode=True)
        return self._parse_json_response(response)

    async def refine_pain_point(
        self, product_description: str, cluster_topic: str, raw_comments: str
    ) -> dict[str, Any]:
        """Refine a raw pain cluster using Insight Miner (Pain + Driver)."""
        context = self._get_pain_context(cluster_topic)
        
        prompt = INSIGHT_MINER_PROMPT_TEMPLATE.format(
            product_description=product_description,
            cluster_topic=cluster_topic,
            pain_context=context,
            raw_comments=raw_comments,
        )
        
        response = await self._generate_text(prompt, json_mode=True)
        return self._parse_json_response(response)

    async def generate_opportunity(
        self, product_description: str, target_community: str, pain_title: str, pain_insight: str = "", root_cause: str = ""
    ) -> dict[str, Any]:
        """Generate a structured opportunity card."""
        prompt = OPPORTUNITY_PROMPT_TEMPLATE.format(
            product_description=product_description,
            target_community=target_community,
            pain_title=pain_title,
            pain_insight=pain_insight,
            root_cause=root_cause,
        )
        
        response = await self._generate_text(prompt, json_mode=True)
        return self._parse_json_response(response)

    async def generate_summary(self, report_content: str) -> str:
        """Generate a simple text summary."""
        prompt = SUMMARY_PROMPT_TEMPLATE.format(report_content=report_content)
        return await self._generate_text(prompt, json_mode=False)