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
        "title": "跨境电商/PayPal",
        "prompt": "PayPal 费用与结算痛点分析，面向跨境电商卖家，聚焦手续费、风控与回款速度问题。",
        "tags": ["跨境电商", "支付"],
        "topic_profile_id": "cross_border_payment_v1",
    },
    {
        "title": "跨境电商/现金流",
        "prompt": "跨境电商卖家多平台回款管理工具，自动预测现金流与结算风险，覆盖 Amazon/Etsy/Shopify。",
        "tags": ["跨境电商"],
        "topic_profile_id": "cross_border_payment_v1",
    },
    {
        "title": "跨境电商/回款费率",
        "prompt": "跨境电商卖家多平台回款与手续费管理工具，覆盖 Amazon/Etsy/Shopify/TikTok Shop，解决结算周期长、费率不透明、资金分散的问题。",
        "tags": ["跨境电商", "支付"],
        "topic_profile_id": "cross_border_payment_v1",
    },
    {
        "title": "SaaS协作",
        "prompt": "远程团队项目管理与协作工具，解决跨时区沟通、任务拆解与进度跟踪问题，关注 Notion/Asana/Trello 的使用痛点与替代机会。",
        "tags": ["SaaS"],
        "topic_profile_id": "saas_collaboration_v1",
    },
    {
        "title": "家居",
        "prompt": "面向北美租房人群的家居收纳与清洁工具推荐/比价助手，解决空间小、产品选择多、踩雷的问题。",
        "tags": ["家居"],
        "topic_profile_id": "vacuum_cleaner_v1",
    },
    {
        "title": "户外",
        "prompt": "我想挖 EDC（everyday carry）里 keychain / pocket organizer 方向的真实需求，重点看用户如何整理钥匙、门禁卡、小刀、手电、耳机，哪些场景会乱、会硌、会丢、不好拿，判断是否适合做小配件或收纳产品。",
        "tags": ["户外"],
        "topic_profile_id": "edc_everyday_carry_v1",
    },
]

_STANDARD_CARD_PROFILE_HINTS: list[tuple[str, tuple[str, ...]]] = [
    (
        "shopify_ads_conversion_v1",
        ("shopify 广告", "shopify ads", "roas", "cpc", "facebookads", "meta ads"),
    ),
    (
        "cross_border_payment_v1",
        ("paypal", "跨境", "回款", "收款", "结算", "费率", "手续费", "payout", "payment", "cashflow"),
    ),
    (
        "vacuum_cleaner_v1",
        ("家居", "收纳", "清洁", "吸尘", "vacuum", "cleaner", "租房", "robot vacuum"),
    ),
    (
        "saas_collaboration_v1",
        ("saas", "协作", "远程团队", "项目管理", "notion", "asana", "trello", "clickup"),
    ),
    (
        "edc_everyday_carry_v1",
        ("户外", "露营", "edc", "钥匙", "口袋", "keychain", "everyday carry", "multitool", "flashlight"),
    ),
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


def infer_topic_profile_id(
    *,
    title: str,
    prompt: str,
    tags: Sequence[str],
    explicit_topic_profile_id: str | None = None,
) -> str | None:
    explicit = (explicit_topic_profile_id or "").strip().lower()
    if explicit:
        return explicit
    text = " ".join(
        part.strip().lower() for part in (title, prompt, " ".join(tags)) if part and part.strip()
    )
    if not text:
        return None
    for profile_id, keywords in _STANDARD_CARD_PROFILE_HINTS:
        if any(keyword in text for keyword in keywords):
            return profile_id
    return None


def build_guidance_examples(
    examples: Iterable[Any],
    *,
    limit: int = 6,
    fallback: Sequence[dict[str, Any]] = _FALLBACK_EXAMPLES,
) -> list[dict[str, Any]]:
    seen_ids: set[str] = set()
    seen_prompts: set[str] = set()
    seen_titles: set[str] = set()
    items: list[dict[str, Any]] = []

    # 首页标准卡是黄金展示入口：优先返回这组固定高质量样板，避免被示例库噪音覆盖。
    for item in fallback:
        prompt = (item.get("prompt") or "").strip()
        title = str(item.get("title", "示例")).strip() or "示例"
        if not prompt or prompt in seen_prompts or title in seen_titles:
            continue
        seen_prompts.add(prompt)
        seen_titles.add(title)
        tags = [str(tag) for tag in item.get("tags", []) if tag]
        items.append(
            {
                "example_id": None,
                "title": title,
                "prompt": prompt,
                "tags": tags,
                "topic_profile_id": infer_topic_profile_id(
                    title=title,
                    prompt=prompt,
                    tags=tags,
                    explicit_topic_profile_id=str(item.get("topic_profile_id", "")).strip() or None,
                ),
            }
        )
        if len(items) >= limit:
            return items

    for example in examples:
        description = (getattr(example, "prompt", "") or "").strip()
        if not description:
            continue
        example_id = getattr(example, "id", None)
        example_key = str(example_id) if example_id else description
        if example_key in seen_ids:
            continue
        title = (getattr(example, "title", "") or "").strip()
        if title and title in seen_titles:
            continue
        seen_ids.add(example_key)
        seen_prompts.add(description)
        if title:
            seen_titles.add(title)
        raw_tags = getattr(example, "tags", None)
        tags = raw_tags if isinstance(raw_tags, list) and raw_tags else infer_guidance_tags(description)
        title = title or tags[0]
        items.append(
            {
                "example_id": str(example_id) if example_id else None,
                "title": title,
                "prompt": description,
                "tags": tags,
                "topic_profile_id": infer_topic_profile_id(
                    title=title,
                    prompt=description,
                    tags=tags,
                    explicit_topic_profile_id=str(getattr(example, "topic_profile_id", "")).strip()
                    or None,
                ),
            }
        )
        if len(items) >= limit:
            return items

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
