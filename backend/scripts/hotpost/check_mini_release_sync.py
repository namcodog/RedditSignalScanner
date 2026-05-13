from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.hotpost.hotpost_supply_contract import get_supply_operation_defaults
from app.services.hotpost.card_content_rules_config import load_card_content_rules


SNAPSHOT_ROOT = ROOT / "data" / "hotpost" / "mini_snapshots"
CF_RELEASE_ROOT = ROOT.parents[0] / "hotpost-mini" / "hotpost-mini-app" / "cloudfunctions" / "miniRelease" / "data"
CF_FAVORITES_ROOT = ROOT.parents[0] / "hotpost-mini" / "hotpost-mini-app" / "cloudfunctions" / "miniFavorites" / "data"
CLOUD_DB_ROOT = SNAPSHOT_ROOT / "cloud_db"
TREND_AUDIT_PATH = ROOT.parents[0] / "reports" / "evals" / "mini-release-trend-audit-latest.json"


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _trend_audit_violations(*, expected_release_id: str | None) -> list[str]:
    payload = _load_json(TREND_AUDIT_PATH)
    if not isinstance(payload, dict):
        return [f"trend audit missing: {TREND_AUDIT_PATH}"]
    latest_release_id = str(payload.get("latest_release_id") or "")
    if expected_release_id and latest_release_id != expected_release_id:
        return [
            f"trend audit release mismatch: expected {expected_release_id}, got {latest_release_id or 'missing'}",
        ]
    return []


def _expected_feed_contract() -> dict[str, int]:
    defaults = get_supply_operation_defaults()
    return {
        "initial_page_size": int(defaults["feed_initial_page_size"]),
        "max_page_size": int(defaults["feed_max_page_size"]),
    }


def _feed_contract(data: dict) -> dict[str, int] | None:
    raw = data.get("feed_contract")
    if not isinstance(raw, dict):
        return None
    if "initial_page_size" not in raw or "max_page_size" not in raw:
        return None
    return {
        "initial_page_size": int(raw["initial_page_size"]),
        "max_page_size": int(raw["max_page_size"]),
    }


def _contract_label(data: dict, *, expected: dict[str, int]) -> str:
    contract = _feed_contract(data)
    if contract is None:
        return "feed_contract=missing"
    status = "ok" if contract == expected else "mismatch"
    return (
        f"feed_contract={contract['initial_page_size']}/{contract['max_page_size']} "
        f"expected={expected['initial_page_size']}/{expected['max_page_size']} "
        f"status={status}"
    )


def _copy_guard_violations(cards: list[dict]) -> list[str]:
    rules = load_card_content_rules()
    banned = rules.get("banned_patterns") or {}
    global_patterns = [str(item).strip() for item in banned.get("global", []) if str(item).strip()]
    field_specific = banned.get("field_specific") or {}
    if not isinstance(field_specific, dict):
        field_specific = {}
    card_fields = ["title", "summary_line", "audience", "why_now"]
    detail_fields = ["pain_point", "target_user_and_scene", "why_test_now", "continue_signal", "stop_signal"]
    violations: list[str] = []
    for card in cards:
        card_id = str(card.get("card_id") or "")
        for field_name in card_fields:
            violations.extend(
                _field_copy_violations(
                    card_id=card_id,
                    field_name=field_name,
                    value=card.get(field_name),
                    global_patterns=global_patterns,
                    field_specific=field_specific,
                )
            )
        detail = card.get("detail") or {}
        if isinstance(detail, dict):
            for field_name in detail_fields:
                violations.extend(
                    _field_copy_violations(
                        card_id=card_id,
                        field_name=f"detail.{field_name}",
                        value=detail.get(field_name),
                        global_patterns=global_patterns,
                        field_specific=field_specific,
                    )
                )
            if "min_test_action" in detail:
                violations.append(f"{card_id}: detail.min_test_action should not be published")
    return violations


def _hot_controversy_violations(cards: list[dict]) -> list[str]:
    violations: list[str] = []
    for card in cards:
        if str(card.get("lane") or "") != "hot":
            continue
        if str(card.get("card_type") or "") != "validate":
            continue
        card_id = str(card.get("card_id") or "")
        if not isinstance(card.get("controversy_chart"), dict):
            violations.append(f"{card_id}: hot validate card missing controversy_chart")
        if not isinstance(card.get("controversy_meta"), dict):
            violations.append(f"{card_id}: hot validate card missing controversy_meta")
    return violations


def _field_copy_violations(
    *,
    card_id: str,
    field_name: str,
    value: object,
    global_patterns: list[str],
    field_specific: dict,
) -> list[str]:
    if not isinstance(value, str):
        return []
    base_name = field_name.rsplit(".", 1)[-1]
    patterns = [*global_patterns, *[str(item).strip() for item in field_specific.get(base_name, []) if str(item).strip()]]
    return [f"{card_id}: {field_name} contains banned pattern {pattern!r}" for pattern in patterns if pattern in value]


def _print_release(label: str, path: Path, *, expected: dict[str, int]) -> bool:
    data = _load_json(path)
    if not isinstance(data, dict):
        print(f"{label}: missing")
        return False
    print(
        f"{label}: release_id={data.get('release_id')} "
        f"card_count={data.get('card_count')} "
        f"published_at={data.get('published_at')} "
        f"{_contract_label(data, expected=expected)}"
    )
    return _feed_contract(data) == expected


def main() -> None:
    print("=== mini release sync status ===")
    expected = _expected_feed_contract()
    ok = True
    ok = _print_release("snapshot latest", SNAPSHOT_ROOT / "latest.json", expected=expected) and ok
    ok = _print_release("miniRelease bundle", CF_RELEASE_ROOT / "latest.json", expected=expected) and ok
    ok = _print_release("miniFavorites bundle", CF_FAVORITES_ROOT / "latest.json", expected=expected) and ok
    snapshot_latest = _load_json(SNAPSHOT_ROOT / "latest.json")
    expected_release_id = str(snapshot_latest.get("release_id") or "") if isinstance(snapshot_latest, dict) else None

    meta = _load_json(CLOUD_DB_ROOT / "mini_release_meta.json")
    cards = _load_json(CLOUD_DB_ROOT / "mini_release_cards.json")

    if isinstance(meta, list) and meta:
        meta_doc = meta[0]
        print(
            "cloud_db meta: "
            f"release_id={meta_doc.get('release_id')} "
            f"card_count={meta_doc.get('card_count')} "
            f"{_contract_label(meta_doc, expected=expected)}"
        )
        ok = (_feed_contract(meta_doc) == expected) and ok
    else:
        print("cloud_db meta: missing")
        ok = False

    if isinstance(cards, list):
        first_title = cards[0].get("title") if cards else None
        print(f"cloud_db cards: count={len(cards)} first_title={first_title}")
        hot_controversy_violations = _hot_controversy_violations(cards)
        if hot_controversy_violations:
            print("cloud_db hot controversy guard: failed")
            for item in hot_controversy_violations[:20]:
                print(f"- {item}")
            if len(hot_controversy_violations) > 20:
                print(f"- ... {len(hot_controversy_violations) - 20} more")
            ok = False
        else:
            print("cloud_db hot controversy guard: ok")
        violations = _copy_guard_violations(cards)
        if violations:
            print("cloud_db copy guard: failed")
            for item in violations[:20]:
                print(f"- {item}")
            if len(violations) > 20:
                print(f"- ... {len(violations) - 20} more")
            ok = False
        else:
            print("cloud_db copy guard: ok")
    else:
        print("cloud_db cards: missing")
        ok = False

    trend_payload = _load_json(TREND_AUDIT_PATH)
    if isinstance(trend_payload, dict):
        print(
            "trend audit: "
            f"latest_release_id={trend_payload.get('latest_release_id')} "
            f"latest_status={trend_payload.get('latest_status')} "
            f"stable_streak={trend_payload.get('stable_streak')} "
            f"remaining_new_releases={trend_payload.get('remaining_new_releases')} "
            f"remediation_focus={trend_payload.get('latest_remediation_focus')}"
        )
    else:
        print("trend audit: missing")
    trend_violations = _trend_audit_violations(expected_release_id=expected_release_id)
    if trend_violations:
        print("trend audit guard: failed")
        for item in trend_violations:
            print(f"- {item}")
        ok = False
    else:
        print("trend audit guard: ok")

    print("collections:")
    print("- mini_release_meta  <- import backend/data/hotpost/mini_snapshots/cloud_db/mini_release_meta.wechat-import.json")
    print("- mini_release_cards <- import backend/data/hotpost/mini_snapshots/cloud_db/mini_release_cards.wechat-import.json")
    print("note: wechat-import files are JSON Lines with .json suffix; use Upsert so stable _id values update existing docs.")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
