from types import SimpleNamespace

from app.api.routes.guidance import build_guidance_examples, infer_guidance_tags


def test_infer_guidance_tags_matches_keywords() -> None:
    tags = infer_guidance_tags("Amazon Shopify 回款与手续费管理工具")
    assert "跨境电商" in tags


def test_build_guidance_examples_dedupe_and_limit() -> None:
    examples = [
        SimpleNamespace(id="example-1", prompt="Amazon Shopify payout tool for sellers", title="跨境电商"),
        SimpleNamespace(id="example-2", prompt="Amazon Shopify payout tool for sellers", title="跨境电商"),
        SimpleNamespace(id="example-3", prompt="camping gear helper for beginners", title="户外"),
    ]

    result = build_guidance_examples(examples, limit=2, fallback=[])

    assert len(result) == 2
    assert result[0]["example_id"] == "example-1"
    assert result[0]["prompt"] == "Amazon Shopify payout tool for sellers"
    assert "跨境电商" in result[0]["tags"]
