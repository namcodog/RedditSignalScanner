from __future__ import annotations

from typing import List, Sequence

from .interfaces import EvidenceText, Summarizer


def _clean_sentence(text: str) -> str:
    s = " ".join((text or "").strip().split())
    # 简单去噪：去掉URL与管道符
    s = s.replace("|", " ")
    return s


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


class LocalExtractiveSummarizer(Summarizer):
    """
    无外部依赖的提取式“要点句”生成器：
    - 取 title 优先；否则用 note；否则空。
    - 截断到指定字数，保证可控且稳定。
    - 该实现作为 LLM 客户端不可用时的最小保障。
    """

    def summarize_evidences(self, evidences: Sequence[EvidenceText], *, max_chars: int = 28) -> list[str]:
        outputs: List[str] = []
        for ev in evidences:
            base = ev.title or ev.note or ""
            sent = _clean_sentence(base)
            if not sent:
                outputs.append("")
                continue
            outputs.append(_truncate(sent, max_chars))
        return outputs


__all__ = ["LocalExtractiveSummarizer"]

