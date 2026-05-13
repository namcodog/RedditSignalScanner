from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class AnchorBridgeRule:
    triggers: tuple[str, ...]
    anchors: tuple[str, ...]


_OPEN_TOPIC_ANCHOR_RULES: tuple[AnchorBridgeRule, ...] = (
    AnchorBridgeRule(
        triggers=("下单", "下单率", "弃单", "购物车"),
        anchors=("checkout", "conversion", "orders"),
    ),
    AnchorBridgeRule(
        triggers=("成交", "转化", "成单", "销量"),
        anchors=("conversion", "sales", "orders"),
    ),
    AnchorBridgeRule(
        triggers=("支付", "付款", "扣费", "拒付", "退款", "回款", "收款"),
        anchors=("payment", "payments", "refund", "payout"),
    ),
    AnchorBridgeRule(
        triggers=("审核", "合规", "风控", "敏感品", "敏感类目", "成人用品"),
        anchors=("compliance", "risk", "trust"),
    ),
    AnchorBridgeRule(
        triggers=("卖", "卖家", "卖货", "售卖", "销售", "店铺", "电商", "跨境"),
        anchors=("seller", "ecommerce", "store"),
    ),
    AnchorBridgeRule(
        triggers=("客服", "售后", "客诉", "投诉", "差评"),
        anchors=("support", "returns", "trust"),
    ),
)


def bridge_open_topic_anchors(
    *,
    description: str,
    existing_keywords: Sequence[str],
) -> list[str]:
    """
    中文开放题的主链补全层：
    - 不直接改 warzone 规则
    - 只把中文经营/交易表达补成英文 anchor
    - 让后续的 Reddit search / semantic search / warzone classifier 能继续按主链自己的规则工作
    """

    desc = str(description or "").strip().lower()
    existing = {str(item or "").strip().lower() for item in existing_keywords if str(item or "").strip()}
    bridged: list[str] = []
    seen = set(existing)

    for rule in _OPEN_TOPIC_ANCHOR_RULES:
        if not any(trigger in desc for trigger in rule.triggers):
            continue
        for anchor in rule.anchors:
            normalized = anchor.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            bridged.append(anchor)

    return bridged


__all__ = ["bridge_open_topic_anchors"]
