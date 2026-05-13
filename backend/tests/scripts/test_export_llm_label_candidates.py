from __future__ import annotations

import importlib

from app.services.llm import label_export_service as export_mod


def _row(
    *,
    comment_id: int,
    body: str,
    category: str,
    business_pool: str = "unscored",
    value_score: float = 0.0,
    score: int = 10,
) -> dict[str, object]:
    return {
        "id": comment_id,
        "body": body,
        "subreddit": "r/test",
        "post_title": f"post-{comment_id}",
        "categories": [category],
        "business_pool": business_pool,
        "value_score": value_score,
        "score": score,
        "post_score": score + 5,
        "post_num_comments": score + 3,
    }


def test_build_comment_activation_export_applies_domain_quota_and_batches() -> None:
    rows = [
        _row(comment_id=1, body="A" * 30, category="Home_Lifestyle", business_pool="core", value_score=9.0),
        _row(comment_id=2, body="B" * 30, category="Home_Lifestyle", business_pool="lab", value_score=6.0),
        _row(comment_id=3, body="C" * 30, category="Ecommerce_Business", business_pool="lab", value_score=5.0),
        _row(comment_id=4, body="D" * 30, category="AI_Workflow", business_pool="unscored", value_score=0.0),
        _row(comment_id=5, body="short", category="AI_Workflow", business_pool="core", value_score=8.0),
        _row(comment_id=6, body="A" * 30, category="Home_Lifestyle", business_pool="core", value_score=8.0),
    ]

    batches, summary = export_mod._build_comment_activation_export(
        rows=rows,
        max_body_chars=120,
        effective_domain_weights={
            "Home_Lifestyle": 30,
            "Ecommerce_Business": 21,
            "AI_Workflow": 5,
        },
        target_total=4,
        base_quota=1,
        first_batch_size=2,
        batch_size=2,
    )

    assert sum(len(batch) for batch in batches) == 4
    assert [len(batch) for batch in batches] == [2, 2]
    assert summary["eligible_comment_pool"] == 4
    assert summary["rule_stats"]["filtered_short"] == 1
    assert summary["rule_stats"]["deduped"] == 1
    assert summary["domain_distribution"]["Home_Lifestyle"] == 2
    assert summary["domain_distribution"]["Ecommerce_Business"] == 1
    assert summary["domain_distribution"]["AI_Workflow"] == 1
    assert summary["batch_plan"] == [{"batch": 1, "size": 2}, {"batch": 2, "size": 2}]


def test_build_comment_activation_export_interleaves_domains() -> None:
    rows = [
        _row(comment_id=1, body="Home one comment body long enough", category="Home_Lifestyle", business_pool="core", value_score=9.0),
        _row(comment_id=2, body="Ecom one comment body long enough", category="Ecommerce_Business", business_pool="core", value_score=8.5),
        _row(comment_id=3, body="Home two comment body long enough", category="Home_Lifestyle", business_pool="lab", value_score=8.0),
        _row(comment_id=4, body="Ecom two comment body long enough", category="Ecommerce_Business", business_pool="lab", value_score=7.5),
    ]

    batches, _summary = export_mod._build_comment_activation_export(
        rows=rows,
        max_body_chars=120,
        effective_domain_weights={
            "Home_Lifestyle": 30,
            "Ecommerce_Business": 21,
        },
        target_total=4,
        base_quota=2,
        first_batch_size=4,
        batch_size=4,
    )

    ordered_domains = [item["domain"] for item in batches[0]]
    assert ordered_domains == [
        "Home_Lifestyle",
        "Ecommerce_Business",
        "Home_Lifestyle",
        "Ecommerce_Business",
    ]


def test_interleave_selected_rows_by_domain_rotates_domains() -> None:
    rows_by_domain = {
        "Home_Lifestyle": [
            {"id": 1, "domain": "Home_Lifestyle"},
            {"id": 2, "domain": "Home_Lifestyle"},
        ],
        "Ecommerce_Business": [
            {"id": 3, "domain": "Ecommerce_Business"},
        ],
        "AI_Workflow": [
            {"id": 4, "domain": "AI_Workflow"},
            {"id": 5, "domain": "AI_Workflow"},
        ],
    }

    rows = export_mod._interleave_selected_rows_by_domain(rows_by_domain)

    assert [row["domain"] for row in rows] == [
        "Home_Lifestyle",
        "AI_Workflow",
        "Ecommerce_Business",
        "Home_Lifestyle",
        "AI_Workflow",
    ]


def test_export_script_main_delegates_to_runtime(
    monkeypatch,
    tmp_path,
) -> None:
    export_script = importlib.import_module("scripts.report.export_llm_label_candidates")
    captured: dict[str, object] = {}
    printed: list[str] = []

    monkeypatch.setattr(
        export_script,
        "get_settings",
        lambda: type(
            "_Settings",
            (),
            {
                "llm_label_post_limit": 11,
                "llm_label_comment_limit": 22,
                "llm_label_lookback_days": 33,
                "llm_label_body_chars": 444,
                "llm_label_comment_chars": 555,
            },
        )(),
    )
    monkeypatch.setattr(
        export_script,
        "run_label_export_cli",
        lambda *, settings, cli_input: captured.update(
            {"settings": settings, "cli_input": cli_input}
        )
        or {"status": "ok", "posts": 1, "comments": 2},
    )
    monkeypatch.setattr(
        export_script.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "_Args",
            (),
            {
                "output_dir": str(tmp_path),
                "post_limit": 11,
                "comment_limit": 22,
                "lookback_days": 33,
                "export_all": False,
                "include_noise": False,
                "noise_ratio": 0.1,
                "noise_min_score": 20,
                "noise_min_comments": 10,
                "top_comments": 2,
                "posts_only": False,
                "comments_only": False,
                "historical_activation": False,
                "activation_target": 100,
                "activation_base_quota": 20,
                "activation_first_batch_size": 50,
                "activation_batch_size": 25,
            },
        )(),
    )
    monkeypatch.setattr("builtins.print", lambda message: printed.append(str(message)))

    export_script.main()

    assert captured["cli_input"].output_dir == tmp_path
    assert printed == ['{"status": "ok", "posts": 1, "comments": 2}']
