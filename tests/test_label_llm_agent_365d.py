import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "label_llm_agent_365d.py"
    spec = importlib.util.spec_from_file_location("label_llm_agent_365d", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_post_ask_help_pricing_and_entity():
    module = _load_module()
    row = {
        "id": 10,
        "subreddit": "r/Shopify",
        "title": "How to reduce PayPal fees?",
        "body": "",
        "url": "",
        "value_score": 0,
        "business_pool": "core",
    }
    out = module.label_post(row)
    assert out["main_intent"] == "ask_help"
    assert out["content_type"] == "ask_question"
    assert "pricing" in out["aspect_tags"]
    assert out["pain_tags"]
    assert "paypal" in out["entities"]["known"]
    assert 0.1 <= out["purchase_intent_score"] <= 0.4


def test_post_complain_account_ban():
    module = _load_module()
    row = {
        "id": 11,
        "subreddit": "r/shopify",
        "title": "Shopify banned my account again",
        "body": "Terrible policy",
        "url": "",
        "value_score": 0,
        "business_pool": "core",
    }
    out = module.label_post(row)
    assert out["main_intent"] == "complain"
    assert out["content_type"] == "rant"
    assert "account_ban" in out["pain_tags"]
    assert out["sentiment"] <= -0.2


def test_comment_share_solution_expert():
    module = _load_module()
    row = {
        "id": 12,
        "subreddit": "r/stripe",
        "post_title": "Payout delays",
        "comment_body": "Fix this by enabling Stripe payouts and waiting 24h.",
    }
    out = module.label_comment(row)
    assert out["main_intent"] == "share_solution"
    assert out["actor_type"] == "expert_sharing"
    assert out["sentiment"] >= 0.1
