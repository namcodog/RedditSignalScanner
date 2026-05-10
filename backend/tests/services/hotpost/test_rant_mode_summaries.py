from app.services.hotpost.rant_mode_summaries import (
    build_compare_insufficient_summary,
    build_compare_no_hit_summary,
    build_quote_only_rant_summary,
)


def _payload_value(entry: dict[str, object], key: str) -> object:
    return entry.get(key)


def test_build_compare_no_hit_summary_is_honest_but_not_hard_fail() -> None:
    summary = build_compare_no_hit_summary()

    assert "没找到足够明确、能站得住的双边原话" in summary
    assert "不给你硬凑比较结论" in summary


def test_build_compare_insufficient_summary_uses_quote_then_sets_boundary() -> None:
    summary = build_compare_insufficient_summary(
        payload={
            "top_quotes": [
                {
                    "quote": "Codex is better for long prompts, but I still switch back sometimes.",
                }
            ]
        },
        get_payload_value=_payload_value,
    )

    assert "先给你看已经找到的原话" in summary
    assert "还不够支撑稳定的双边比较结论" in summary


def test_build_quote_only_rant_summary_without_quote_keeps_boundary_clear() -> None:
    summary = build_quote_only_rant_summary([], payload={}, get_payload_value=_payload_value)

    assert "先不给你硬凑结论" in summary
    assert "先把边界说清楚" in summary
