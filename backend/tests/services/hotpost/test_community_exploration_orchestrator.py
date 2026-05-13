from __future__ import annotations

import pytest

from app.services.hotpost.community_exploration_orchestrator import (
    ExplorationProbe,
    parse_probe_arg,
    run_exploration_pre_stage,
    run_exploration_post_stage,
)


@pytest.mark.asyncio
async def test_pre_stage_runs_probe_without_formal_persist(monkeypatch) -> None:
    calls: list[tuple[str, int | None, str]] = []

    async def fake_probe(
        scope_id: str, *, max_candidates: int | None = None, mode: str = "safe"
    ) -> dict[str, object]:
        calls.append((scope_id, max_candidates, mode))
        return {
            "scope_id": scope_id,
            "items": [{"candidate_id": f"cand-{scope_id}-1"}],
            "experimental_only": True,
            "persisted_to_formal_candidates": False,
            "experimental_candidate_store": {
                "path": f"backend/data/hotpost/experimental_candidates/{scope_id}.json",
                "candidate_count": 1,
            },
        }

    monkeypatch.setattr(
        "app.services.hotpost.community_exploration_orchestrator.collect_experimental_scope_probe",
        fake_probe,
    )

    result = await run_exploration_pre_stage(
        probes=[ExplorationProbe(scope_id="ai-automation", max_candidates=6)],
        report_date="2026-05-12",
    )

    assert calls == [("ai-automation", 6, "safe")]
    assert result["stage"] == "pre"
    assert result["contracts"]["writes_formal_candidates"] is False
    assert result["contracts"]["writes_db"] is False
    assert result["summary"]["probe_count"] == 1
    assert result["summary"]["experimental_candidate_count"] == 1
    assert result["probes"][0]["persisted_to_formal_candidates"] is False


@pytest.mark.asyncio
async def test_post_stage_builds_audit_and_feedback_without_db_write(
    monkeypatch,
) -> None:
    def fake_audit(report_date=None) -> dict[str, object]:
        return {
            "schema_version": "hotpost-community-discovery-audit/v1",
            "report_date": "2026-05-12",
            "contracts": {"writes_db": False, "auto_promote": False},
            "rows": [
                {
                    "community": "r/aeo",
                    "published_count": 1,
                    "suggested_action": "keep_testing",
                }
            ],
        }

    def fake_feedback(audit_payload, *, pool_community_keys) -> dict[str, object]:
        return {
            "schema_version": "hotpost-community-pool-feedback-dry-run/v1",
            "contracts": {
                "writes_db": False,
                "auto_promote": False,
                "requires_human_review": True,
            },
            "summary": {
                "input_rows": 1,
                "already_in_pool": 0,
                "promote_candidate": 0,
                "keep_testing": 1,
                "reject": 0,
            },
            "rows": [],
        }

    monkeypatch.setattr(
        "app.services.hotpost.community_exploration_orchestrator.build_current_community_discovery_audit",
        fake_audit,
    )
    monkeypatch.setattr(
        "app.services.hotpost.community_exploration_orchestrator.build_pool_feedback_dry_run",
        fake_feedback,
    )

    result = await run_exploration_post_stage(
        report_date="2026-05-12",
        pool_community_keys=set(),
    )

    assert result["stage"] == "post"
    assert result["contracts"]["writes_db"] is False
    assert result["contracts"]["writes_formal_candidates"] is False
    assert result["summary"]["audit_rows"] == 1
    assert result["summary"]["promote_candidate"] == 0
    assert result["summary"]["keep_testing"] == 1


def test_parse_probe_arg_accepts_scope_count_and_direction() -> None:
    probe = parse_probe_arg("ai-automation:6:AI工具")

    assert probe.scope_id == "ai-automation"
    assert probe.max_candidates == 6
    assert probe.direction == "AI工具"


def test_parse_probe_arg_accepts_scope_only() -> None:
    probe = parse_probe_arg("ecommerce-sellers")

    assert probe.scope_id == "ecommerce-sellers"
    assert probe.max_candidates is None
    assert probe.direction == ""


def test_parse_probe_arg_rejects_missing_scope() -> None:
    with pytest.raises(ValueError, match="probe must use"):
        parse_probe_arg("")
