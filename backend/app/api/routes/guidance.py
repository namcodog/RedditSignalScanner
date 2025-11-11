from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/guidance", tags=["guidance"])  # mounted under /api


@router.get("/input", summary="结构化输入指导与示例")
async def get_input_guidance() -> dict:
    """返回分析页的文案建议与可用性提示（后端提供，前端可直接渲染）。"""
    return {
        "placeholder": "请用1–2句话说明：领域/目标/时间窗/关注点（示例见下方）",
        "tips": [
            "领域（Crypto/AI/SaaS/跨境等）+ 输出类型（榜单/痛点/机会）",
            "时间窗（7天/30天）+ 关注指标（热度/增速/情绪）",
            "包含/排除的关键词或社区 + 期望输出规模（Top N）",
            "每条建议至少绑定2条证据 URL，便于复核",
        ],
        "examples": [
            {
                "title": "Crypto 榜单",
                "prompt": "寻找近30天涨势明显的 L2 话题，排除meme；输出Top10并给证据链接。",
            },
            {
                "title": "AI 机会",
                "prompt": "7天内关于 AI 助手在远程团队的痛点与解决方案，输出机会Top5，证据≥2。",
            },
            {
                "title": "SaaS 竞品",
                "prompt": "30天内 Notion/Trello 对比的常见诉求，标注强弱项与示例帖子。",
            },
        ],
    }


__all__ = ["router"]

