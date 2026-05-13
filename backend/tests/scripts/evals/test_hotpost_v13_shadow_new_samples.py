from __future__ import annotations

from backend.scripts.evals.run_hotpost_v13_shadow_new_samples import (
    CARD_TIMEOUT_SECONDS,
    REPORT_JSON_PATH,
    REPORT_MD_PATH,
    V13_PROFILE_ID,
    render_review_packet,
    write_outputs,
)


def test_v13_shadow_uses_distinct_read_only_review_artifacts() -> None:
    assert V13_PROFILE_ID == "hotpost_v13_title_standalone"
    assert REPORT_JSON_PATH.name == "hotpost_v13_shadow_new_samples_results.json"
    assert REPORT_MD_PATH.name == "hotpost_v13_shadow_new_samples_review_packet.md"
    assert CARD_TIMEOUT_SECONDS == 240.0


def test_v13_shadow_review_packet_compares_v12_and_v13_title_layers() -> None:
    report = render_review_packet(
        [
            {
                "context": {
                    "lane": "signal",
                    "card_id": "card-1",
                    "source_scope_id": "ai-automation",
                    "topic_pack_id": "agent-builder",
                    "score": 123,
                    "num_comments": 45,
                    "source_link": "https://reddit.com/r/test/comments/card-1",
                    "evidence_quotes": [
                        {
                            "community": "r/test",
                            "text": "Users are asking what the 800-line prompt actually does.",
                        }
                    ],
                },
                "semantic_model": "google/gemini-3-flash-preview",
                "writer_model": "deepseek/deepseek-v4-pro",
                "semantic_brief": {
                    "core_scene": "开发者在追问大提示词到底解决什么问题。",
                    "writing_focus": "别写成提示词越长越好。",
                    "risk_bounds": "不能说所有 prompt 工程都无效。",
                    "avoid_claims": ["不要写成 AI 代理已经失败。"],
                },
                "input_baseline": {"title": "旧标题"},
                "v12_shadow": {"title": "V12 标题"},
                "v13_shadow": {"title": "V13 标题"},
                "fluency_repair_issue_count": 0,
                "remaining_density_issues": [],
                "v13_title_issues_before": ["title: issue"],
                "v13_title_issues_after": [],
                "error": "",
            }
        ]
    )

    assert "# Hotpost V13 Shadow 新样本人工审核包" in report
    assert "V12 shadow 输出" in report
    assert "V13 title-standalone 输出" in report
    assert "语义理解 brief" in report
    assert "开发者在追问大提示词到底解决什么问题" in report
    assert "title 残留问题 `0`" in report
    assert "google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro" in report


def test_v13_shadow_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_v13_shadow_new_samples as shadow

    monkeypatch.setattr(shadow, "REPORT_JSON_PATH", tmp_path / "results.json")
    monkeypatch.setattr(shadow, "REPORT_MD_PATH", tmp_path / "report.md")

    json_path, md_path = write_outputs([])

    assert json_path.name == "results.json"
    assert md_path.name == "report.md"
    assert json_path.exists()
    assert md_path.exists()
