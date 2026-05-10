from app.services.hotpost.hot_exploration_rules import SOURCE_SCOPES, WHY_NOW_RULES
from app.services.hotpost.card_payload_store import load_cards_payload


def test_hotpost_card_content_contract_is_aligned() -> None:
    payload = load_cards_payload()

    assert [item["category_id"] for item in payload["categories"]] == ["all", "validate", "write"]
    assert isinstance(payload["candidates"], list)
    assert isinstance(payload["drafts"], list)

    for item in payload["published"]:
        assert item["category_id"] == item["card_type"]
        assert item["source_scope_id"] in SOURCE_SCOPES
        assert item["source_scope_name"] == SOURCE_SCOPES[item["source_scope_id"]]["title"]
        assert item["why_now_reason"] in WHY_NOW_RULES
