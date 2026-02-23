from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis.keyword_extraction import extract_keywords
from app.db.read_scopes import get_comments_core_lab_relation

try:
    # 仅类型引用与可选注入；测试中可传入自定义 Fake 客户端
    from app.services.llm.clients.openai_client import OpenAIChatClient  # type: ignore
except Exception:  # pragma: no cover - 仅为运行环境兜底
    OpenAIChatClient = object  # type: ignore


@dataclass
class PersonaResult:
    community: str
    persona_label: str
    traits: List[str]
    strategy: str
    confidence: float
    method: Literal["llm", "rules"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "community": self.community,
            "persona_label": self.persona_label,
            "traits": self.traits,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "method": self.method,
        }


class PersonaGenerator:
    """社区画像生成器：
    - 无 LLM 时走规则引擎
    - 有 LLM 时优先走 LLM，失败则降级规则
    """

    def __init__(self, llm_client: OpenAIChatClient | None = None, *, persona_rules: dict[str, dict[str, Any]] | None = None) -> None:  # type: ignore[name-defined]
        self._llm = llm_client

        # 简易可配置规则：关键词 → (label, traits, strategy)
        # 可通过 persona_rules 覆盖，满足“可配置”要求
        default_rules: dict[str, dict[str, Any]] = {
            "subscription": {
                "label": "反订阅派",
                "traits": ["讨厌订阅", "注重一次性买断"],
                "strategy": "从反订阅角度切入",
            },
            "price": {
                "label": "性价比党",
                "traits": ["在乎价格", "追求价值"],
                "strategy": "从性价比角度切入",
            },
            "diy": {
                "label": "DIY建设",
                "traits": ["动手能力强", "偏好自控"],
                "strategy": "提供教程与清单",
            },
            "open": {
                "label": "开源拥趸",
                "traits": ["反SaaS", "重视自由度"],
                "strategy": "强调开源替代方案",
            },
        }
        self._rules: dict[str, dict[str, Any]] = persona_rules or default_rules

    async def generate_batch(
        self,
        session: AsyncSession,
        communities: Sequence[str],
        pain_points: Sequence[Dict[str, Any]] | None = None,  # 未用到，预留
    ) -> List[PersonaResult]:
        results: list[PersonaResult] = []
        for sub in communities:
            # 抓取社区样本文本（comments），拼接后做关键词提取
            texts = await self._fetch_recent_texts(session, sub)
            corpus = "\n".join(texts) if texts else ""
            try:
                kw = await extract_keywords(corpus or "no data here", max_keywords=100)
                keywords = kw.keywords
            except Exception as exc:
                logger.warning("extract_keywords failed for community=%s: %s", sub, exc)
                keywords = []

            if self._llm is not None:
                res = self._generate_llm_safe(sub, keywords)
                if res is not None:
                    results.append(res)
                    continue

            # 兜底：规则引擎
            results.append(self._generate_rules(sub, keywords))
        return results

    async def _fetch_recent_texts(self, session: AsyncSession, community: str) -> list[str]:
        sub = community.lower().lstrip("r/")
        comments_rel = await get_comments_core_lab_relation(session)
        rows = await session.execute(
            text(
                f"""
                SELECT body FROM {comments_rel}
                WHERE lower(subreddit) IN (:r1, :r2)
                ORDER BY created_utc DESC
                LIMIT 200
                """
            ),
            {"r1": sub, "r2": f"r/{sub}"},
        )
        return [str(r[0]) for r in rows.fetchall() if r and r[0]]

    # ---------------- LLM ----------------

    def _generate_llm_safe(self, community: str, keywords: list[str]) -> PersonaResult | None:
        try:
            return self._generate_llm(community, keywords)
        except Exception as exc:
            logger.warning("Persona LLM generation failed for %s: %s", community, exc)
            return None

    def _generate_llm(self, community: str, keywords: List[str]) -> PersonaResult:
        if self._llm is None:
            raise RuntimeError("LLM client not provided")

        # 精简 prompt，约束输出格式；真实实现可参考 title_slogan 模式
        sys_prompt = (
            "你是市场分析助理。根据关键词生成社区画像："
            "输出严格为：label|trait1,trait2|strategy|confidence(0-1)。只输出一行。"
        )
        user_prompt = f"社区: {community}\n关键词: {', '.join(keywords[:20])}"
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ]
        content = self._llm._chat_completion(messages, max_tokens=64, temperature=0.2)  # type: ignore[attr-defined]
        label, traits, strategy, confidence = self._parse_llm_payload(content)
        return PersonaResult(
            community=community,
            persona_label=label or "画像",
            traits=traits or ["用户导向", "关注价值"],
            strategy=strategy or "从痛点角度切入",
            confidence=confidence if confidence is not None else 0.75,
            method="llm",
        )

    @staticmethod
    def _parse_llm_payload(text: str) -> tuple[str | None, list[str], str | None, float | None]:
        t = (text or "").strip().splitlines()[0].strip()
        # 优先解析管道分隔：label|trait1,trait2|strategy|0.88
        if "|" in t:
            parts = [p.strip() for p in t.split("|")]
            label = parts[0] if len(parts) > 0 else None
            traits = [s.strip() for s in (parts[1].split(",") if len(parts) > 1 and parts[1] else []) if s.strip()]
            strategy = parts[2] if len(parts) > 2 else None
            try:
                conf = float(parts[3]) if len(parts) > 3 else None
            except Exception:
                conf = None
            return label or None, traits, strategy or None, conf
        # 退化：无法解析
        return None, [], None, None

    # ---------------- Rules ----------------

    def _generate_rules(self, community: str, keywords: List[str]) -> PersonaResult:
        text = " ".join(k.lower() for k in keywords)
        chosen = None
        for k, meta in self._rules.items():
            if k in text:
                chosen = meta
                break
        if chosen is None:
            chosen = {"label": "探索者", "traits": ["乐于尝试", "关注性价比"], "strategy": "从共情与价值入手"}

        label = str(chosen.get("label", "画像"))
        traits = [str(x) for x in (chosen.get("traits") or [])][:6]
        strategy = str(chosen.get("strategy", "从痛点角度切入"))
        return PersonaResult(
            community=community,
            persona_label=label,
            traits=traits if traits else ["关注价值"],
            strategy=strategy,
            confidence=0.65,
            method="rules",
        )


__all__ = ["PersonaGenerator", "PersonaResult"]
logger = logging.getLogger(__name__)
