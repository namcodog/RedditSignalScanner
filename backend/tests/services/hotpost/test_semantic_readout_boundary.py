from __future__ import annotations

from pathlib import Path


HOTPOST_SERVICE_DIR = Path(__file__).resolve().parents[3] / "app" / "services" / "hotpost"


def test_card_content_generator_uses_semantic_readout_not_pack_overrides() -> None:
    source = (HOTPOST_SERVICE_DIR / "card_content_generator.py").read_text(encoding="utf-8")
    blocked_tokens = [
        "agent_builder_signal_overrides",
        "business_growth_signal_overrides",
        "category_winds_overrides",
        "organic_discovery_overrides",
        "paid_econ_signal_overrides",
        "selection_signal_overrides",
        "apply_agent_builder_signal_readout_overrides",
        "apply_business_growth_signal_polish",
        "apply_category_winds_readout_overrides",
        "apply_organic_discovery_readout_overrides",
        "apply_paid_econ_signal_readout_overrides",
        "apply_selection_signal_readout_overrides",
        "selection_signal_prompt_extra",
        "variant_extra_instruction",
        "variant_why_now_override",
    ]

    assert "semantic_readout" in source
    for token in blocked_tokens:
        assert token not in source


def test_signal_skill_variant_policy_is_not_allowed_to_own_pack_copy() -> None:
    source = (HOTPOST_SERVICE_DIR / "signal_skill_variant_policy.py").read_text(encoding="utf-8")
    blocked_tokens = [
        'topic_pack_id == "paid-economics"',
        "出海投放从业者",
        "先别急着调预算",
        "营销人开始重新算一笔账",
        "用户开始嫌贵",
        "prompt engineering",
    ]

    for token in blocked_tokens:
        assert token not in source


def test_signal_skill_experiment_uses_semantic_readout_not_old_overrides() -> None:
    source = (HOTPOST_SERVICE_DIR / "signal_skill_experiment.py").read_text(encoding="utf-8")
    blocked_tokens = [
        "paid_econ_signal_overrides",
        "apply_paid_econ_signal_readout_overrides",
        "variant_extra_instruction",
        'why_test_now": why_now',
    ]

    assert "semantic_readout" in source
    assert "from app.services.hotpost.card_content_polish import" not in source
    for token in blocked_tokens:
        assert token not in source


def test_pack_specific_override_modules_are_removed() -> None:
    removed_modules = [
        "agent_builder_signal_overrides.py",
        "business_growth_signal_overrides.py",
        "category_winds_overrides.py",
        "organic_discovery_overrides.py",
        "paid_econ_signal_overrides.py",
        "selection_signal_overrides.py",
    ]

    for module in removed_modules:
        assert not (HOTPOST_SERVICE_DIR / module).exists()


def test_new_card_generation_does_not_import_legacy_copy_builders() -> None:
    source = (HOTPOST_SERVICE_DIR / "card_content_generator.py").read_text(encoding="utf-8")

    assert "legacy_signal_copy_builder" not in source
    assert "build_signal_why_now" not in source
    assert "build_signal_why_test_now" not in source
    assert "build_continue_signal" not in source
    assert "build_stop_signal" not in source


def test_card_content_polish_is_only_legacy_publish_polish_shell() -> None:
    source = (HOTPOST_SERVICE_DIR / "card_content_polish.py").read_text(encoding="utf-8")

    assert "PUBLISHED_CARD_OVERRIDES" in source
    assert "polish_published_card" in source
    assert "_GENERIC_REPLACEMENTS" not in source
    assert "_CLIENT_JARGON_REPLACEMENTS" not in source
    assert "def build_signal_why_now" not in source
    assert '"build_signal_why_now"' not in source
    assert len(source.splitlines()) <= 140
