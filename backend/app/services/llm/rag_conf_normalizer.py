from __future__ import annotations

import json
from typing import Sequence, Tuple

from app.services.llm.clients.openai_client import OpenAIChatClient


def _tokenize(s: str) -> set[str]:
    s = "".join(ch.lower() if ch.isalnum() else " " for ch in (s or ""))
    parts = [p for p in s.split() if p]
    return set(parts)


class LocalRagConfidenceNormalizer:
    """
    简易置信归一化：基于 token Jaccard 相似度并考虑前后缀一致性。
    仅用于 OpenAI 不可用时的兜底。
    """

    def normalize(self, name: str, *, candidates: Sequence[str]) -> Tuple[str | None, float]:
        src_tokens = _tokenize(name)
        best: tuple[str | None, float] = (None, 0.0)
        for cand in candidates:
            cand_tokens = _tokenize(cand)
            if not cand_tokens:
                continue
            inter = len(src_tokens & cand_tokens)
            union = len(src_tokens | cand_tokens) or 1
            jacc = inter / union
            # 轻度前缀/后缀加分
            extra = 0.0
            low_src = (name or "").lower().strip()
            low_cand = (cand or "").lower().strip()
            if low_src.startswith(low_cand) or low_cand.startswith(low_src):
                extra += 0.1
            score = min(1.0, jacc + extra)
            if score > best[1]:
                best = (cand, score)
        return best


class OpenAIRagConfidenceNormalizer:
    """
    RAG 限定 + 置信度：只允许在候选中选择；输出 JSON {choice, confidence}。
    """

    def __init__(self, model: str, *, timeout: float = 6.0) -> None:
        self._client = OpenAIChatClient(model, timeout=timeout)

    def normalize(self, name: str, *, candidates: Sequence[str]) -> Tuple[str | None, float]:
        # 构造紧凑候选文本，避免 prompt 过大
        cand_text = "\n".join(f"- {c}" for c in candidates)
        system = (
            "你是实体规范化助手。只能在候选列表中选择一个最佳匹配；若无匹配，输出 NONE。"
            "严格输出 JSON：{""choice"": <候选或NONE>, ""confidence"": <0..1>}。"
            "confidence=0 表示几乎不确定；>=0.8 表示很确定。"
        )
        user = f"候选列表:\n{cand_text}\n\n实体名称: {name}\n\n只输出 JSON："
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        raw = self._client._chat_completion(messages, max_tokens=64, temperature=0.1)
        try:
            data = json.loads((raw or "").strip())
            choice = (data.get("choice") or "").strip()
            conf = float(data.get("confidence", 0.0) or 0.0)
            if choice.upper() == "NONE":
                return (None, max(0.0, min(1.0, conf)))
            # 必须在候选中
            for c in candidates:
                if choice.lower() == c.lower():
                    return (c, max(0.0, min(1.0, conf)))
            return (None, max(0.0, min(1.0, conf)))
        except Exception:
            return (None, 0.0)


__all__ = ["LocalRagConfidenceNormalizer", "OpenAIRagConfidenceNormalizer"]

