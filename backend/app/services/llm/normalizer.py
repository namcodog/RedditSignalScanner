from __future__ import annotations

from typing import Sequence


class LocalDeterministicNormalizer:
    """
    简单的本地归一化：大小写去空格匹配；不中则返回 None。
    作为 LLM 不可用时的兜底方案。
    """

    def normalize(self, name: str, *, candidates: Sequence[str]) -> str | None:
        source = (name or "").strip().lower()
        if not source:
            return None
        for cand in candidates:
            if (cand or "").strip().lower() == source:
                return cand
        return None


__all__ = ["LocalDeterministicNormalizer"]

