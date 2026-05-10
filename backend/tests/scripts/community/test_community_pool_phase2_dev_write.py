from __future__ import annotations

from scripts.community.community_pool_phase2_dev_write import render_markdown


def test_render_markdown_shows_write_plan_and_rollback() -> None:
    payload = {
        "phase": "community-pool-phase2-dev-write",
        "dry_run": True,
        "database": "reddit_signal_scanner_dev",
        "summary": {
            "input_rows": 69,
            "would_insert": 64,
            "inserted": 0,
            "skipped_existing": 5,
            "blocked_deleted_conflicts": 0,
        },
        "inserted_names": [],
        "skipped_existing": ["r/OpenAI"],
        "blocked_deleted_conflicts": [],
        "rollback_sql": "reports/community-governance/phase2-dev-write-rollback.sql",
    }

    markdown = render_markdown(payload)

    assert "- DB writes: `false`" in markdown
    assert "- target_database: `reddit_signal_scanner_dev`" in markdown
    assert "- input_rows: `69`" in markdown
    assert "- would_insert: `64`" in markdown
    assert "- inserted: `0`" in markdown
    assert "- skipped_existing: `5`" in markdown
    assert "- rollback_sql:" in markdown
