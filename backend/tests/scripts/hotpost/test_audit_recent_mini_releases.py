from __future__ import annotations

import os
from pathlib import Path
import json

from app.services.hotpost.mini_release_trend_audit import (
    DEFAULT_BASELINE_RELEASE_ID,
    audit_recent_release_payloads,
)
from scripts.hotpost.audit_recent_mini_releases import run_release_trend_audit


def _card(
    *,
    card_id: str,
    published_at: str,
    source_scope_id: str,
    topic_pack_id: str,
    top_community: str,
) -> dict:
    return {
        "card_id": card_id,
        "published_at": published_at,
        "source_scope_id": source_scope_id,
        "topic_pack_id": topic_pack_id,
        "top_community": top_community,
    }


def _healthy_release(release_id: str, published_at: str) -> dict:
    cards: list[dict] = []
    communities = {
        "ai-automation": [
            "r/OpenAI",
            "r/ChatGPT",
            "r/ClaudeAI",
            "r/LocalLLaMA",
            "r/LLM",
        ],
        "business-growth-ops": [
            "r/juststart",
            "r/SEO",
            "r/Entrepreneur",
            "r/DigitalMarketing",
            "r/GrowthHacking",
        ],
        "ecommerce-sellers": [
            "r/shopify",
            "r/FulfillmentByAmazon",
            "r/ecommerce",
            "r/Flipping",
            "r/BuyItForLife",
        ],
    }
    packs = {
        "ai-automation": "upstream-winds",
        "business-growth-ops": "organic-discovery",
        "ecommerce-sellers": "selection-signals",
    }
    index = 0
    for repeat in range(10):
        for scope in ("ai-automation", "business-growth-ops", "ecommerce-sellers"):
            index += 1
            community_pool = communities[scope]
            cards.append(
                _card(
                    card_id=f"{release_id}-{index}",
                    published_at=f"2026-04-17T07:{59-index:02d}:00Z",
                    source_scope_id=scope,
                    topic_pack_id=packs[scope],
                    top_community=community_pool[(repeat + index) % len(community_pool)],
                )
            )
    return {
        "release_id": release_id,
        "published_at": published_at,
        "cards": cards,
    }


def _with_supplement_cards(payload: dict, *, count: int = 12) -> dict:
    release = json.loads(json.dumps(payload))
    cards = list(release.get("cards") or [])
    for card in cards:
        card["surface_bucket"] = "main"
    for index in range(1, count + 1):
        cards.append(
            {
                "card_id": f"{release['release_id']}-supplement-{index}",
                "published_at": release["published_at"],
                "source_scope_id": "business-growth-ops",
                "topic_pack_id": "paid-economics",
                "top_community": "r/FacebookAds",
                "surface_bucket": "supplement",
            }
        )
    release["cards"] = cards
    release["main_card_count"] = len(payload.get("cards") or [])
    release["supplement_card_count"] = count
    return release


def test_audit_recent_release_payloads_keeps_baseline_as_watching() -> None:
    baseline = _healthy_release(DEFAULT_BASELINE_RELEASE_ID, "2026-04-17T08:00:00Z")

    summary = audit_recent_release_payloads([baseline])

    assert summary["latest_release_id"] == DEFAULT_BASELINE_RELEASE_ID
    assert summary["latest_status"] == "watching"
    assert summary["observed_new_releases"] == 0
    assert summary["stable_streak"] == 0
    assert summary["remaining_new_releases"] == 5


def test_audit_recent_release_payloads_only_becomes_stable_after_five_new_qualified_releases() -> None:
    releases = [
        _healthy_release(DEFAULT_BASELINE_RELEASE_ID, "2026-04-17T08:00:00Z"),
        _healthy_release("release-1", "2026-04-18T08:00:00Z"),
        _healthy_release("release-2", "2026-04-19T08:00:00Z"),
        _healthy_release("release-3", "2026-04-20T08:00:00Z"),
        _healthy_release("release-4", "2026-04-21T08:00:00Z"),
        _healthy_release("release-5", "2026-04-22T08:00:00Z"),
    ]

    summary = audit_recent_release_payloads(releases)
    latest = summary["release_summaries"][0]

    assert summary["latest_release_id"] == "release-5"
    assert summary["latest_status"] == "stable"
    assert summary["observed_new_releases"] == 5
    assert summary["stable_streak"] == 5
    assert summary["remaining_new_releases"] == 0
    assert latest["stability"]["qualified_for_stable"] is True
    assert latest["stability"]["front30_stable"] is True
    assert latest["stability"]["full_inventory_stable"] is True


def test_audit_recent_release_payloads_flags_rebound_when_watched_counts_increase() -> None:
    previous = _healthy_release("release-prev", "2026-04-18T08:00:00Z")
    current = _healthy_release("release-current", "2026-04-19T08:00:00Z")
    for index in range(6):
        current["cards"][index]["top_community"] = "r/FacebookAds"
        current["cards"][index]["topic_pack_id"] = "paid-economics"

    summary = audit_recent_release_payloads([previous, current], baseline_release_id="release-baseline")
    latest = summary["release_summaries"][0]

    assert latest["release_id"] == "release-current"
    assert latest["status"] == "rebound"
    assert "r/FacebookAds" in latest["trend"]["community_rebounds"]
    assert "paid-economics" in latest["trend"]["pack_rebounds"]


def test_audit_recent_release_payloads_ignores_supplement_surface_rebounds() -> None:
    previous = _with_supplement_cards(_healthy_release("release-prev", "2026-04-18T08:00:00Z"), count=0)
    current = _with_supplement_cards(_healthy_release("release-current", "2026-04-19T08:00:00Z"))

    summary = audit_recent_release_payloads([previous, current], baseline_release_id="release-baseline")
    latest = summary["release_summaries"][0]

    assert latest["release_id"] == "release-current"
    assert latest["card_count"] == 30
    assert latest["total_card_count"] == 42
    assert latest["supplement_card_count"] == 12
    assert latest["trend"]["community_rebounds"] == []
    assert latest["trend"]["pack_rebounds"] == []
    assert latest["status"] == "watching"


def test_run_release_trend_audit_writes_default_report(tmp_path: Path) -> None:
    releases_dir = tmp_path / "releases"
    releases_dir.mkdir(parents=True)
    for payload in [
        _healthy_release(DEFAULT_BASELINE_RELEASE_ID, "2026-04-17T08:00:00Z"),
        _healthy_release("release-1", "2026-04-18T08:00:00Z"),
    ]:
        (releases_dir / f"{payload['release_id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    output_path = tmp_path / "mini-release-trend-audit-latest.json"
    summary = run_release_trend_audit(releases_dir=releases_dir, output=output_path)

    assert output_path.exists()
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted["latest_release_id"] == "release-1"
    assert persisted["latest_status"] == summary["latest_status"]


def test_run_release_trend_audit_prefers_most_recent_release_file_when_published_at_ties(tmp_path: Path) -> None:
    releases_dir = tmp_path / "releases"
    releases_dir.mkdir(parents=True)
    baseline = _healthy_release(DEFAULT_BASELINE_RELEASE_ID, "2026-04-17T08:00:00Z")
    first = _healthy_release("release-a", "2026-04-18T08:00:00Z")
    second = _healthy_release("release-b", "2026-04-18T08:00:00Z")

    baseline_path = releases_dir / f"{baseline['release_id']}.json"
    first_path = releases_dir / f"{first['release_id']}.json"
    second_path = releases_dir / f"{second['release_id']}.json"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    first_path.write_text(json.dumps(first, ensure_ascii=False, indent=2), encoding="utf-8")
    second_path.write_text(json.dumps(second, ensure_ascii=False, indent=2), encoding="utf-8")

    os.utime(first_path, (2_000_000_020, 2_000_000_020))
    os.utime(second_path, (2_000_000_010, 2_000_000_010))

    output_path = tmp_path / "mini-release-trend-audit-latest.json"
    summary = run_release_trend_audit(releases_dir=releases_dir, output=output_path)

    assert summary["latest_release_id"] == "release-a"
