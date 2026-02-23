import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "label_empty_tags_posts.py"
    spec = importlib.util.spec_from_file_location("label_empty_tags_posts", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_ask_help_maps_to_ask_question_and_pricing():
    module = _load_module()
    data = {
        "id": 1,
        "subreddit": "r/Shopify",
        "title": "How to lower PayPal fees?",
        "body": "",
        "url": "",
        "value_score": 0,
        "business_pool": "core",
    }
    out = module.label_post(data)
    assert out["main_intent"] == "ask_help"
    assert out["content_type"] == "ask_question"
    assert "pricing" in out["aspect_tags"]


def test_complain_maps_to_rant_with_pain_tag():
    module = _load_module()
    data = {
        "id": 2,
        "subreddit": "r/paypal",
        "title": "PayPal froze my account and support never replies",
        "body": "",
        "url": "",
        "value_score": 0,
        "business_pool": "core",
    }
    out = module.label_post(data)
    assert out["main_intent"] == "complain"
    assert out["content_type"] == "rant"
    assert out["pain_tags"]


def test_offtopic_allows_empty_tags():
    module = _load_module()
    data = {
        "id": 3,
        "subreddit": "r/pics",
        "title": "My cat is sleeping",
        "body": "",
        "url": "",
        "value_score": 0,
        "business_pool": "lab",
    }
    out = module.label_post(data)
    assert out["main_intent"] == "offtopic"
    assert out["pain_tags"] == []
    assert out["aspect_tags"] == []
