from __future__ import annotations

from types import SimpleNamespace

from scripts.community.reconcile_truth_sources import _parse_names, _single_result_payload


def test_parse_names_supports_repeat_and_csv() -> None:
    assert _parse_names(["r/edc,r/multitools", "r/onebag"]) == [
        "r/edc",
        "r/multitools",
        "r/onebag",
    ]


def test_single_result_payload_handles_missing_result() -> None:
    assert _single_result_payload(None) == {"found": False}


def test_single_result_payload_serializes_sync_result() -> None:
    payload = _single_result_payload(
        SimpleNamespace(
            community_name="r/edc",
            registry_id=18,
            memberships_written=1,
            governance_written=1,
            runtime_state_written=True,
        )
    )
    assert payload == {
        "found": True,
        "community_name": "r/edc",
        "registry_id": 18,
        "memberships_written": 1,
        "governance_written": 1,
        "runtime_state_written": True,
    }
