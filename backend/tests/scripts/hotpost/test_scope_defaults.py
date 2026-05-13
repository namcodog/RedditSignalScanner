from __future__ import annotations

import json


def test_run_offline_publish_plan_defaults_to_all_scope(monkeypatch, capsys) -> None:
    import scripts.hotpost.run_offline_publish_plan as mod

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "Args",
            (),
            {
                "limit": None,
                "scope": None,
                "all_scope": False,
                "output": None,
            },
        )(),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit=None, scope=None: captured.update({"limit": limit, "scope": scope}) or {"scope": scope, "publish_list": []},
    )

    mod.main()

    assert captured["scope"] is None
    assert json.loads(capsys.readouterr().out)["scope"] is None


def test_run_offline_publish_plan_scope_flag_still_allows_local_repair(monkeypatch, capsys) -> None:
    import scripts.hotpost.run_offline_publish_plan as mod

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "Args",
            (),
            {
                "limit": None,
                "scope": "business-growth-ops",
                "all_scope": False,
                "output": None,
            },
        )(),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit=None, scope=None: captured.update({"limit": limit, "scope": scope}) or {"scope": scope, "publish_list": []},
    )

    mod.main()

    assert captured["scope"] == "business-growth-ops"
    assert json.loads(capsys.readouterr().out)["scope"] == "business-growth-ops"


def test_audit_topic_tree_governance_defaults_to_all_scope(monkeypatch, capsys) -> None:
    import scripts.hotpost.audit_topic_tree_governance as mod

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "Args",
            (),
            {
                "limit": None,
                "scope": None,
                "all_scope": False,
                "output": None,
            },
        )(),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit=None, scope=None: captured.update({"limit": limit, "scope": scope}) or {
            "generated_at": "2026-04-17T00:00:00Z",
            "scope": scope,
            "topic_tree_governance": {
                "overall_decision": "publish",
                "scopes": {
                    "ai-automation": {
                        "overall_decision": "publish",
                        "allocation": {"decision": "publish"},
                        "rotation": {"decision": "publish"},
                        "supply": {"decision": "publish"},
                        "source_health": {"decision": "publish"},
                    }
                },
            },
        },
    )

    mod.main()

    assert captured["scope"] is None
    payload = json.loads(capsys.readouterr().out)
    assert payload["scope"] is None
    assert payload["scope_summaries"]["ai-automation"]["allocation"] == "publish"


def test_audit_topic_tree_governance_scope_flag_still_allows_local_repair(monkeypatch, capsys) -> None:
    import scripts.hotpost.audit_topic_tree_governance as mod

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "Args",
            (),
            {
                "limit": None,
                "scope": "business-growth-ops",
                "all_scope": False,
                "output": None,
            },
        )(),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit=None, scope=None: captured.update({"limit": limit, "scope": scope}) or {
            "generated_at": "2026-04-17T00:00:00Z",
            "scope": scope,
            "topic_tree_governance": {
                "overall_decision": "publish",
                "scopes": {
                    "business-growth-ops": {
                        "overall_decision": "publish",
                        "allocation": {"decision": "publish"},
                        "rotation": {"decision": "publish"},
                        "supply": {"decision": "publish"},
                        "source_health": {"decision": "publish"},
                    }
                },
            },
        },
    )

    mod.main()

    assert captured["scope"] == "business-growth-ops"
    payload = json.loads(capsys.readouterr().out)
    assert payload["scope"] == "business-growth-ops"
    assert payload["scope_summaries"]["business-growth-ops"]["rotation"] == "publish"
