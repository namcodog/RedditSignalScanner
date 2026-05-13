from __future__ import annotations

import json
from pathlib import Path

from app.scripts_support.env_loader import load_backend_env


def test_run_signal_shadow_compare_scores_flags(tmp_path: Path) -> None:
    load_backend_env()
    import scripts.hotpost.run_signal_shadow_compare as mod

    row = {
        "title": "title",
        "summary_line": "原话里有个关键句：...",
        "audience": "做 Meta 的投手，尤其是那些天天盯消耗的人",
        "why_now": "why",
        "detail": {"why_test_now": "翻过来就是：..."},
    }

    flags = mod._score_flags(row)

    assert "ellipsis" in flags
    assert "translationese" in flags
    assert "audience_tail" in flags


def test_run_signal_shadow_compare_writes_summary(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_signal_shadow_compare as mod

    candidate = type(
        "Candidate",
        (),
        {
            "candidate_id": "cand-1",
            "source_scope_id": "ai-automation",
            "source_scope_name": "AI 与自动化",
            "topic_pack_id": "upstream-winds",
        },
    )()

    monkeypatch.setattr(mod, "load_signal_shadow_candidates", lambda **_kwargs: [candidate])

    async def _fake_generate(_candidate, *, client_factory):
        _ = client_factory
        return {
            "candidate_id": "cand-1",
            "title": "title",
            "summary_line": "summary",
            "audience": "audience",
            "why_now": "why",
            "detail": {"why_test_now": "evidence"},
        }

    monkeypatch.setattr(mod, "generate_signal_shadow_from_candidate", _fake_generate)

    out = tmp_path / "compare.jsonl"
    summary = __import__("asyncio").run(
        mod._run(
            type(
                "Args",
                (),
                {
                    "snapshot_id": "queue-1",
                    "candidate_id": [],
                    "limit": 1,
                    "cli_model": "gemini-3.1-pro-preview",
                    "codex_model": "gpt-5.4-mini",
                    "timeout_seconds": 180.0,
                    "output_jsonl": str(out),
                },
            )()
        )
    )

    assert summary["generated_count"] == 1
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["candidate_id"] == "cand-1"
    assert rows[0]["api_flags"] == []
    assert rows[0]["cli_flags"] == []
    assert rows[0]["codex_flags"] == []
