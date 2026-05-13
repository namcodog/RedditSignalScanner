from __future__ import annotations

from app.schemas.hotpost_signal import SourceScopeId, WhyNowReason


SOURCE_SCOPES: dict[SourceScopeId, dict[str, str]] = {
    "ai-automation": {
        "title": "AI 与自动化",
        "description": "聚焦 AI 工具、工作流、coding、内容生产、技术变化与趋势。",
    },
    "ecommerce-sellers": {
        "title": "电商与卖家",
        "description": "聚焦选品、品类需求、市场切入、卖家反馈与消费文化变化。",
    },
    "business-growth-ops": {
        "title": "商业增长与运营",
        "description": "聚焦获客、转化、客服、销售、运营效率与商机信号。",
    },
}

WHY_NOW_RULES: dict[WhyNowReason, dict[str, str]] = {
    "new_threads_24h": {
        "title": "24 小时内冒出新 thread",
        "description": "说明这不是旧存量话题，今天确实还有新增讨论。",
    },
    "new_comments_24h": {
        "title": "24 小时内讨论继续发酵",
        "description": "说明用户还在追着聊，不是单个帖子孤立冒头。",
    },
    "recurring_7d": {
        "title": "近 7 天反复出现",
        "description": "说明同类问题已经不是个例，开始形成持续信号。",
    },
    "switch_signal_7d": {
        "title": "近 7 天出现替换或求解法动作",
        "description": "说明讨论已经从吐槽走向动作，开始找替代或找解法。",
    },
}
