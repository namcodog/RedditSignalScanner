from __future__ import annotations

from app.services.report.content_guardrails import (
    clean_business_terms,
    contains_meta_leak,
    contains_systemy_copy,
    is_low_signal_business_text,
    is_low_signal_opportunity_title,
    is_low_signal_scaffold_pain_title,
    is_placeholder_pain_title,
    looks_like_marketplace_listing,
    looks_like_raw_post_title,
    sanitize_business_text,
)


def test_clean_business_terms_filters_short_noise_tokens() -> None:
    assert clean_business_terms(["ad", "att", "black", "自动重试回款", "多平台聚合"]) == [
        "自动重试回款",
        "多平台聚合",
    ]


def test_clean_business_terms_filters_english_fragment_noise() -> None:
    assert clean_business_terms(
        ["SaaS founders think", "would love EDC Suggestions of quality items in black", "跨平台费率对比"]
    ) == ["跨平台费率对比"]


def test_contains_meta_leak_flags_system_copy() -> None:
    assert contains_meta_leak("这是系统生成的统一结构报告，不依赖前端拼装。") is True
    assert contains_meta_leak("基于真实抱怨提炼出的产品机会。") is False


def test_looks_like_raw_post_title_detects_question_style_copy() -> None:
    assert looks_like_raw_post_title("Suggestions to complete my Matte Black EDC") is True
    assert looks_like_raw_post_title("would love EDC Suggestions of quality items in black") is True
    assert looks_like_raw_post_title("多平台回款聚合器") is False


def test_looks_like_marketplace_listing_detects_trade_post_copy() -> None:
    assert (
        looks_like_marketplace_listing(
            "[WTS] Blade Show Texas is TOMORROW and I need space and money lol"
        )
        is True
    )
    assert looks_like_marketplace_listing("Timestamp: https://imgur.com/a/demo") is True
    assert looks_like_marketplace_listing("口袋减负收纳夹") is False


def test_contains_systemy_copy_flags_machine_judgement() -> None:
    assert contains_systemy_copy("痛点销售比极低，立即投放PayPal替代测试广告。") is True
    assert contains_systemy_copy("先验证印度用户payout帖，再决定是否深挖。") is True
    assert contains_systemy_copy("供需缺口明显，建议先去 r/stripe 看高频抱怨。") is False


def test_sanitize_business_text_rejects_systemy_copy_when_requested() -> None:
    assert (
        sanitize_business_text(
            "痛点销售比极低，立即投放PayPal替代测试广告。",
            fallback="进场信号：强烈建议",
            reject_systemy=True,
        )
        == "进场信号：强烈建议"
    )


def test_placeholder_pain_helpers_flag_keypoint_and_empty_highfreq_titles() -> None:
    assert is_placeholder_pain_title("关键痛点 2") is True
    assert is_placeholder_pain_title("高频抱怨") is True
    assert is_low_signal_scaffold_pain_title("高频抱怨：Is seal deeper") is True
    assert is_placeholder_pain_title("流程一旦跨工具切换，信息和动作就容易断开") is False


def test_low_signal_opportunity_title_helper_rejects_generic_and_scaffold_copy() -> None:
    assert is_low_signal_opportunity_title("产品机会") is True
    assert is_low_signal_opportunity_title("产品机会：need a mobile app to be successful") is True
    assert is_low_signal_opportunity_title("高频抱怨：Would love EDC suggestions") is True
    assert is_low_signal_opportunity_title("围绕「支付插件配置卡壳」的产品机会") is False


def test_is_low_signal_business_text_rejects_moderation_noise_fragments() -> None:
    assert is_low_signal_business_text("Can't post poll in this subreddit because account too new") is True
    assert is_low_signal_business_text("This post was removed by moderators, please use the weekly thread") is True
    assert is_low_signal_business_text(
        "I analyzed 147,895 reddit across 10,543 Reddit discussions in /r/flashlight"
    ) is True
    assert is_low_signal_business_text("回款冻结导致现金流断档，店铺补货被迫延后") is False
