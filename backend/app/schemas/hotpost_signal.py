from __future__ import annotations

from typing import Literal


SourceScopeId = Literal[
    "ai-automation",
    "ecommerce-sellers",
    "business-growth-ops",
]
SignalLevel = Literal["hot", "rising", "sustained"]
ToneTag = Literal["实战", "求解法", "吐槽", "迁移", "趋势", "复盘"]
WhyNowReason = Literal[
    "new_threads_24h",
    "new_comments_24h",
    "recurring_7d",
    "switch_signal_7d",
]


__all__ = [
    "SignalLevel",
    "SourceScopeId",
    "ToneTag",
    "WhyNowReason",
]
