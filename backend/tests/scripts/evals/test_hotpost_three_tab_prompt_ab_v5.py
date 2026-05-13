from __future__ import annotations

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v5 import (
    SEMANTIC_MODEL,
    WRITER_MODEL,
    _generate_json_without_response_format,
    render_v5_markdown_report,
    write_outputs,
)


def test_v5_uses_gemini_flash_and_deepseek_v4_pro() -> None:
    assert SEMANTIC_MODEL == "google/gemini-3-flash-preview"
    assert WRITER_MODEL == "deepseek/deepseek-v4-pro"


def test_v5_report_uses_distinct_title_and_model_route() -> None:
    report = render_v5_markdown_report(
        [
            {
                "lane": "signal",
                "card_id": "signal-1",
                "model": "google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro",
                "baseline": {"title": "旧标题"},
                "variant": {"title": "新标题"},
            }
        ]
    )

    assert "# Hotpost 三 Tab Prompt A/B v5 flash-deepseek 小样本报告" in report
    assert "google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro" in report


def test_v5_writes_distinct_artifacts(tmp_path, monkeypatch) -> None:
    from backend.scripts.evals import run_hotpost_three_tab_prompt_ab_v5 as v5

    monkeypatch.setattr(v5, "REPORTS_EVALS_DIR", tmp_path)

    json_path, md_path = write_outputs([])

    assert json_path.name == "hotpost_three_tab_prompt_ab_v5_flash_deepseek_results.json"
    assert md_path.name == "hotpost_three_tab_prompt_ab_v5_flash_deepseek_report.md"
    assert json_path.exists()
    assert md_path.exists()


async def test_v5_deepseek_json_generation_omits_response_format() -> None:
    class FakeClient:
        async def generate(self, messages, *, response_format, temperature, max_tokens):
            assert response_format is None
            assert messages
            assert temperature == 0.2
            assert max_tokens == 64
            return '{"title":"ok"}'

    payload = await _generate_json_without_response_format(
        model="deepseek/deepseek-v4-pro",
        timeout=10.0,
        messages=[{"role": "user", "content": "return json"}],
        client_factory=lambda model, timeout: FakeClient(),
        max_tokens=64,
    )

    assert payload == {"title": "ok"}
