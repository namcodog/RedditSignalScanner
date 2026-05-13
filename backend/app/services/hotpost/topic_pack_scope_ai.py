from __future__ import annotations


AI_TOPIC_PACKS = [
    {
        "topic_pack_id": "upstream-winds",
        "title": "上游风向",
        "description": "大厂风向、GitHub 开源、模型发布、平台变化。",
        "target_share": 25,
        "subreddits": ["artificial", "OpenAI", "LocalLLaMA", "MachineLearning"],
        "keywords": {
            "category": ["github release", "open source model", "model launch", "api pricing", "frontier model"],
            "problem": ["rate limit", "deprecation", "license change", "governance"],
            "change": ["breakthrough", "release notes", "benchmark jump", "adoption shift"],
        },
    },
    {
        "topic_pack_id": "tools-efficiency",
        "title": "工具与效率",
        "description": "AI 工具、效率、workflow、skills、SOP、copilot 使用变化。",
        "target_share": 35,
        "subreddits": ["ChatGPT", "ClaudeAI", "OpenAI", "cursor"],
        "keywords": {
            "category": ["ai workflow with fewer tools", "too many ai subscriptions", "context loss between tools"],
            "problem": ["tool switching fatigue", "copy paste context between tools", "re explaining context to ai", "using too many ai tools", "context switching between chatgpt and claude"],
            "change": ["which ai tool did you cancel", "which ai subscription was worth keeping", "replaced multiple ai tools with one", "stopped paying for ai tools", "which ai tool did you keep"],
        },
    },
    {
        "topic_pack_id": "agent-builder",
        "title": "Builder 基建",
        "description": "LLM、agent、context、eval、orchestration、可靠性。",
        "target_share": 40,
        "subreddits": ["ChatGPTCoding", "ClaudeAI", "OpenAI", "cursor", "automation"],
        "keywords": {
            "category": [
                "agent evaluation",
                "tool calling workflow",
                "agent observability",
                "multi step agent workflow",
            ],
            "problem": [
                "agent broke in production",
                "tool calling unreliable",
                "context loss in agent loop",
                "agent ignored tool result",
                "agent fails after multiple steps",
            ],
            "change": [
                "stopped using agent framework",
                "replaced agent stack",
                "cut agent steps",
                "moved from agent to workflow",
                "agent eval caught bug",
            ],
        },
    },
]
