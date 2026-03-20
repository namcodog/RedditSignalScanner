from types import SimpleNamespace

from app.api.routes.guidance import build_guidance_examples, infer_guidance_tags


def test_infer_guidance_tags_matches_keywords() -> None:
    tags = infer_guidance_tags("Amazon Shopify 回款与手续费管理工具")
    assert "跨境电商" in tags


def test_build_guidance_examples_dedupe_and_limit() -> None:
    examples = [
        SimpleNamespace(
            id="example-1",
            prompt="Amazon Shopify payout tool for sellers",
            title="跨境电商",
            topic_profile_id="cross_border_payment_v1",
        ),
        SimpleNamespace(id="example-2", prompt="Amazon Shopify payout tool for sellers", title="跨境电商"),
        SimpleNamespace(id="example-3", prompt="camping gear helper for beginners", title="户外"),
    ]

    result = build_guidance_examples(examples, limit=2, fallback=[])

    assert len(result) == 2
    assert result[0]["example_id"] == "example-1"
    assert result[0]["prompt"] == "Amazon Shopify payout tool for sellers"
    assert result[0]["topic_profile_id"] == "cross_border_payment_v1"
    assert "跨境电商" in result[0]["tags"]


def test_build_guidance_examples_infers_topic_profile_for_standard_cards() -> None:
    examples = [
        SimpleNamespace(
            id="example-paypal",
            prompt="PayPal 费用与结算痛点分析，面向跨境电商卖家，聚焦手续费、风控与回款速度问题。",
            title="跨境电商/PayPal",
            tags=["跨境电商", "支付"],
        ),
        SimpleNamespace(
            id="example-saas",
            prompt="远程团队项目管理与协作工具，解决跨时区沟通、任务拆解与进度跟踪问题，关注 Notion/Asana/Trello 的使用痛点与替代机会。",
            title="SaaS协作",
            tags=["SaaS"],
        ),
        SimpleNamespace(
            id="example-edc",
            prompt="户外露营与日常随身工具（EDC）选购与评测助手，帮助新手挑选高性价比装备，减少踩坑。",
            title="户外",
            tags=["户外"],
        ),
    ]

    result = build_guidance_examples(examples, limit=3, fallback=[])

    assert result[0]["topic_profile_id"] == "cross_border_payment_v1"
    assert result[1]["topic_profile_id"] == "saas_collaboration_v1"
    assert result[2]["topic_profile_id"] == "edc_everyday_carry_v1"
