from __future__ import annotations

from typing import Any, Iterable, Sequence

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.example_library import ExampleLibrary

router = APIRouter(prefix="/guidance", tags=["guidance"])  # mounted under /api


_FALLBACK_EXAMPLES = [
    {
        "title": "跨境电商",
        "prompt": "跨境电商卖家多平台回款与手续费管理工具，覆盖 Amazon/Etsy/Shopify/TikTok Shop，解决结算周期长、费率不透明、资金分散的问题。",
        "tags": ["跨境电商"],
    },
    {
        "title": "跨境电商",
        "prompt": "跨境电商卖家多平台回款管理工具，自动预测现金流与结算风险，覆盖 Amazon/Etsy/Shopify。",
        "tags": ["跨境电商"],
    },
    {
        "title": "跨境支付",
        "prompt": "PayPal 费用与结算痛点分析，面向跨境电商卖家，聚焦手续费、风控与回款速度问题。",
        "tags": ["跨境电商", "支付"],
    },
    {
        "title": "户外/EDC",
        "prompt": "户外露营与日常随身工具（EDC）选购与评测助手，帮助新手挑选高性价比装备，减少踩坑。",
        "tags": ["户外", "EDC"],
    },
    {
        "title": "家居收纳",
        "prompt": "面向北美租房人群的家居收纳与清洁工具推荐/比价助手，解决空间小、产品选择多、踩雷的问题。",
        "tags": ["家居", "收纳"],
    },
    {
        "title": "SaaS/协作",
        "prompt": "远程团队与初创公司项目管理工具，解决协作混乱、信息分散和进度追踪难的问题。",
        "tags": ["SaaS", "协作"],
    },
]

_TAG_RULES: list[tuple[str, Sequence[str]]] = [
    ("跨境电商", ("amazon", "etsy", "shopify", "tiktok", "跨境", "回款", "结算", "电商")),
    ("支付", ("paypal", "payment", "payout", "费率", "手续费", "风控")),
    ("家居", ("家居", "收纳", "清洁", "租房", "home")),
    ("户外", ("露营", "户外", "camp", "gear", "edc")),
    ("SaaS", ("saas", "project", "协作", "项目管理", "远程", "team")),
    ("AI", ("ai", "assistant", "agent", "自动化")),
]


def infer_guidance_tags(description: str) -> list[str]:
    text = (description or "").lower()
    tags: list[str] = []
    for tag, keywords in _TAG_RULES:
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags or ["其他"]


def build_guidance_examples(
    examples: Iterable[Any],
    *,
    limit: int = 6,
    fallback: Sequence[dict[str, Any]] = _FALLBACK_EXAMPLES,
) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    seen_prompts: set[str] = set()
    items: list[dict[str, Any]] = []

    for example in examples:
        description = (getattr(example, "prompt", "") or "").strip()
        if not description:
            continue
        example_id = getattr(example, "id", None)
        example_key = str(example_id) if example_id else description
        if example_key in seen_ids:
            continue
        seen_ids.add(example_key)
        seen_prompts.add(description)
        raw_tags = getattr(example, "tags", None)
        tags = raw_tags if isinstance(raw_tags, list) and raw_tags else infer_guidance_tags(description)
        title = (getattr(example, "title", "") or "").strip() or tags[0]
        items.append(
            {
                "example_id": str(example_id) if example_id else None,
                "title": title,
                "prompt": description,
                "tags": tags,
            }
        )
        if len(items) >= limit:
            return items

    if len(items) < limit:
        for item in fallback:
            prompt = (item.get("prompt") or "").strip()
            if not prompt or prompt in seen_prompts:
                continue
            seen_prompts.add(prompt)
            items.append(
                {
                    "example_id": None,
                    "title": item.get("title", "示例"),
                    "prompt": prompt,
                    "tags": item.get("tags", []),
                }
            )
            if len(items) >= limit:
                break

    return items


@router.get("/input", summary="结构化输入指导与示例")
async def get_input_guidance(db: AsyncSession = Depends(get_session)) -> dict:
    """返回分析页的文案建议与可用性提示（后端提供，前端可直接渲染）。"""
    result = await db.execute(
        select(ExampleLibrary)
        .where(ExampleLibrary.is_active.is_(True))
        .order_by(desc(ExampleLibrary.updated_at), desc(ExampleLibrary.created_at))
        .limit(50)
    )
    example_rows = result.scalars().all()

    return {
        "placeholder": "请用1–2句话说明：领域/目标/时间窗/关注点（示例见下方）",
        "tips": [
            "领域（跨境/家居/户外/SaaS/AI 等）+ 输出类型（榜单/痛点/机会）",
            "时间窗（7天/30天）+ 关注指标（热度/增速/情绪）",
            "包含/排除的关键词或社区 + 期望输出规模（Top N）",
            "每条建议至少绑定2条证据 URL，便于复核",
        ],
        "examples": build_guidance_examples(example_rows),
    }


__all__ = ["router", "build_guidance_examples", "infer_guidance_tags"]
