from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import pytest

from backend.scripts.hotpost import run_v13_published_shadow_refresh as mod


def test_safe_defaults_and_selectors() -> None:
    args = mod.parse_args(["--lane", "signal", "--limit", "2", "--offset", "3", "--card-id", "card-1"])

    assert args.lane == ["signal"]
    assert args.limit == 2
    assert args.offset == 3
    assert args.card_id == ["card-1"]
    assert not hasattr(args, "apply")
    assert mod.V13_PROFILE_ID == "hotpost_v13_title_standalone"
    assert mod.CARD_TIMEOUT_SECONDS == 240.0


def test_select_cards_filters_offsets_and_resume() -> None:
    cards = [
        _published_card("card-1", lane="signal"),
        _published_card("card-2", lane="hot"),
        _published_card("card-3", lane="signal"),
        _published_card("card-4", lane="signal"),
    ]
    selected = mod.select_published_cards(
        cards,
        card_ids=set(),
        lanes={"signal"},
        limit=1,
        offset=1,
        completed_card_ids={"card-3"},
    )

    assert [card["card_id"] for card in selected] == ["card-4"]


def test_write_outputs_uses_distinct_plan_and_report(tmp_path: Path) -> None:
    plan_path, report_path = mod.write_outputs(
        [_row("card-1")],
        output_prefix=tmp_path / "shadow-pilot",
    )

    assert plan_path == tmp_path / "shadow-pilot.json"
    assert report_path == tmp_path / "shadow-pilot.md"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")
    assert plan["kind"] == mod.PLAN_KIND
    assert plan["profile_id"] == mod.V13_PROFILE_ID
    assert plan["selected"] == 1
    assert "## signal · card-1" in report
    assert "原卡" in report
    assert "语义理解 brief" in report
    assert "不要写成全部 CRM 都失败" in report
    assert "V13 候选新版" in report


@pytest.mark.asyncio
async def test_run_shadow_writes_plan_without_merging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def _fake_refresh(card, **_kwargs):
        row = _row(card["card_id"])
        row["original_card"] = card
        row["refreshed_card"] = {**card, "title": "新版标题"}
        row["changed"] = {"title": {"before": card["title"], "after": "新版标题"}}
        return row

    def _boom_merge(_cards):
        raise AssertionError("shadow mode must not merge published cards")

    monkeypatch.setattr(mod, "load_published_cards", lambda: [_published_card("card-1")])
    monkeypatch.setattr(mod, "refresh_one_card", _fake_refresh)
    monkeypatch.setattr(mod, "merge_published_cards", _boom_merge)

    result = await mod.run(
        argparse.Namespace(
            card_id=[],
            lane=[],
            limit=1,
            offset=0,
            workers=1,
            resume_from=None,
            output_prefix=tmp_path / "shadow",
            apply_plan=None,
            approved_by_human=False,
            allow_error_free_only=False,
            json=False,
        )
    )

    assert result["mode"] == "shadow"
    assert result["selected"] == 1
    assert result["generated"] == 1
    assert Path(result["plan_path"]).exists()


@pytest.mark.asyncio
async def test_refresh_one_card_retries_transient_generation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def _flaky_generate(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("LLMClientError: openai: IncompleteRead(209 bytes read)")
        return (
            {"title": "旧标题"},
            {"core_scene": "旧卡语义", "avoid_claims": ["不要放大"]},
            {"title": "V12 标题"},
            {"title": "新版标题", "summary_line": "新版摘要", "audience": "新版读者", "why_now": "新版变化"},
            [],
            [],
            [],
            [],
        )

    monkeypatch.setattr(mod.v13_shadow, "generate_v13_shadow", _flaky_generate)
    monkeypatch.setattr(mod, "build_backfill_draft", lambda card: card)
    monkeypatch.setattr(mod, "merge_semantic_refresh", lambda original, regenerated: {**original, **regenerated})

    row = await mod.refresh_one_card(
        _published_card("card-1"),
        rules={},
        models={},
        banned=[],
        semantic_model="google/gemini-3-flash-preview",
        writer_model="deepseek/deepseek-v4-pro",
    )

    assert calls == 2
    assert row["error"] == ""
    assert row["semantic_brief"]["core_scene"] == "旧卡语义"
    assert row["refreshed_card"]["title"] == "新版标题"


@pytest.mark.asyncio
async def test_refresh_one_card_rewrites_final_candidate_before_merge(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _generate_with_low_density_terms(*_args, **_kwargs):
        return (
            {"title": "旧标题"},
            {"core_scene": "低密度语义", "avoid_claims": ["不要放大"]},
            {"title": "V12 标题"},
            {
                "title": "新版标题",
                "summary_line": "这说明判断依据已经从 A 转移到了 B",
                "audience": "新版读者",
                "why_now": "这改变了用户判断。",
            },
            [],
            [],
            [],
            [],
        )

    monkeypatch.setattr(mod.v13_shadow, "generate_v13_shadow", _generate_with_low_density_terms)
    monkeypatch.setattr(mod, "build_backfill_draft", lambda card: card)
    monkeypatch.setattr(mod, "merge_semantic_refresh", lambda original, regenerated: {**original, **regenerated})

    row = await mod.refresh_one_card(
        _published_card("card-1"),
        rules={
            "semantic_readout": {
                "rewrite_phrases": {
                    "这说明判断依据已经从 A 转移到了 B": "判断重点从 A 转向 B",
                    "这改变了": "变化是",
                }
            }
        },
        models={},
        banned=[],
        semantic_model="google/gemini-3-flash-preview",
        writer_model="deepseek/deepseek-v4-pro",
    )

    assert row["error"] == ""
    assert row["refreshed_card"]["summary_line"] == "判断重点从 A 转向 B。"
    assert row["refreshed_card"]["why_now"] == "变化是用户判断。"


def test_apply_plan_requires_human_approval(tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_plan([_row("card-1")]), ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="--approved-by-human"):
        mod.apply_plan(plan_path, approved_by_human=False, allow_error_free_only=False)


def test_rewrite_generated_candidate_applies_final_title_polish() -> None:
    result = mod.rewrite_generated_candidate(
        {
            "title": "产品经理怀疑这是AI代理训练陷阱",
            "summary_line": "这说明判断依据已经从 A 转移到了 B",
        },
        rules={
            "semantic_readout": {
                "rewrite_phrases": {
                    "这说明判断依据已经从 A 转移到了 B": "判断重点从 A 转向 B",
                }
            }
        },
    )

    assert result["title"] == "产品经理怀疑这是 AI 代理训练陷阱"
    assert result["summary_line"] == "判断重点从 A 转向 B。"


def test_apply_plan_rejects_error_rows(tmp_path: Path) -> None:
    bad = _row("card-1")
    bad["error"] = "TimeoutError: card generation exceeded 240s"
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_plan([bad]), ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="contains failed rows"):
        mod.apply_plan(plan_path, approved_by_human=True, allow_error_free_only=False)


def test_apply_plan_merges_refreshed_cards_and_preserves_identity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original = _published_card("card-1", lane="hot")
    refreshed = {**original, "title": "新版标题", "published_at": "2026-04-01T00:00:00Z"}
    row = _row("card-1")
    row["original_card"] = original
    row["refreshed_card"] = refreshed
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_plan([row]), ensure_ascii=False), encoding="utf-8")
    merged_cards: list[dict] = []

    def _fake_merge(cards: list[dict]) -> int:
        merged_cards.extend(cards)
        return len(cards)

    monkeypatch.setattr(mod, "merge_published_cards", _fake_merge)

    result = mod.apply_plan(plan_path, approved_by_human=True, allow_error_free_only=True)

    assert result["mode"] == "apply_plan"
    assert result["merged"] == 1
    assert merged_cards[0]["card_id"] == "card-1"
    assert merged_cards[0]["lane"] == "hot"
    assert merged_cards[0]["card_type"] == "validate"
    assert merged_cards[0]["source_link"] == "https://reddit.test/q1"


def _plan(rows: list[dict]) -> dict:
    return {
        "kind": mod.PLAN_KIND,
        "plan_version": mod.PLAN_VERSION,
        "profile_id": mod.V13_PROFILE_ID,
        "selected": len(rows),
        "cards": rows,
    }


def _row(card_id: str) -> dict:
    original = _published_card(card_id)
    refreshed = {**original, "title": "新版标题"}
    return {
        "card_id": card_id,
        "lane": original["lane"],
        "card_type": original["card_type"],
        "profile_id": mod.V13_PROFILE_ID,
        "semantic_model": "google/gemini-3-flash-preview",
        "writer_model": "deepseek/deepseek-v4-pro",
        "semantic_brief": {
            "core_scene": "销售团队在讨论 CRM 回填负担。",
            "writing_focus": "讲清楚这一步到底帮不帮销售赢单。",
            "risk_bounds": "不能说全部 CRM 都失败。",
            "avoid_claims": ["不要写成全部 CRM 都失败。"],
        },
        "original_card": original,
        "v12_shadow": {"title": "V12 标题"},
        "refreshed_card": refreshed,
        "changed": {"title": {"before": original["title"], "after": "新版标题"}},
        "fluency_repair_issue_count": 0,
        "remaining_density_issues": [],
        "v13_title_issues_before": [],
        "v13_title_issues_after": [],
        "error": "",
    }


def _published_card(card_id: str, *, lane: str = "signal") -> dict:
    return {
        "card_id": card_id,
        "card_type": "validate",
        "lane": lane,
        "category_id": "validate",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 与自动化",
        "source_event_at": "2026-04-01T00:00:00Z",
        "title": "旧标题",
        "summary_line": "旧摘要",
        "audience": "旧读者",
        "why_now": "旧为什么现在看",
        "published_at": "2026-04-01T00:00:00Z",
        "source_link": "https://reddit.test/q1",
        "quotes": [{"text": "quote one", "community": "r/test", "permalink": "https://reddit.test/q1"}],
        "preview_quote": {"text": "quote one", "community": "r/test", "permalink": "https://reddit.test/q1"},
        "source_module": {"primary_communities": ["r/test"], "thread_count": 1, "community_count": 1},
        "detail": {
            "pain_point": "旧痛点",
            "target_user_and_scene": "旧场景",
            "why_test_now": "旧证据判断",
            "continue_signal": "旧继续观察",
            "stop_signal": "旧停止条件",
        },
    }
