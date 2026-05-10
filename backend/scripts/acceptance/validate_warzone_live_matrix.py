#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from app.services.discovery.warzone_classifier import WarzoneClassifier

VALID_TIERS = {"A_full", "B_trimmed", "C_scouting"}
_PAIN_PLACEHOLDER_RE = re.compile(r"^(关键痛点|痛点|pain point)\s*\d*$", re.IGNORECASE)
_GENERIC_OPPORTUNITY_RE = re.compile(r"^(产品机会|机会)\s*\d*$", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _txt(value: Any) -> str:
    return str(value or "").strip()


def _contains_cjk(value: Any) -> bool:
    return bool(_CJK_RE.search(_txt(value)))


def _is_placeholder_pain(title: str) -> bool:
    text = _txt(title)
    if not text:
        return True
    if _PAIN_PLACEHOLDER_RE.match(text):
        return True
    if text.startswith("高频抱怨"):
        if "：" not in text and ":" not in text:
            return True
        suffix = text.split("：", 1)[-1] if "：" in text else text.split(":", 1)[-1]
        suffix = suffix.strip()
        if not suffix:
            return True
        return not _contains_cjk(suffix)
    return False


def _is_low_signal_opportunity(title: str) -> bool:
    text = _txt(title)
    if not text:
        return True
    if _GENERIC_OPPORTUNITY_RE.match(text):
        return True
    if text.startswith("产品机会："):
        suffix = text.split("：", 1)[-1].strip()
        if not suffix or not _contains_cjk(suffix):
            return True
    if text.startswith("高频抱怨"):
        return True
    if "关键痛点" in text:
        return True
    return False


def _semantic_warzone_mismatch(
    *,
    expected_warzone: str,
    text: str,
    classifier: WarzoneClassifier | None,
) -> bool:
    if classifier is None:
        return False
    cleaned = _txt(text)
    if not cleaned:
        return False
    guess = classifier.classify_texts([cleaned])
    guessed = _txt(guess.warzone)
    confidence = float(guess.confidence or 0.0)
    if not guessed or guessed == "unknown" or confidence < 0.55:
        return False
    return guessed != expected_warzone


def _load_classifier() -> WarzoneClassifier | None:
    config_path = Path(__file__).resolve().parents[2] / "config" / "warzones.yaml"
    if not config_path.exists():
        return None
    try:
        return WarzoneClassifier(config_path)
    except Exception:
        return None


def _validate_row(
    row: dict[str, Any],
    index: int,
    *,
    classifier: WarzoneClassifier | None,
) -> list[str]:
    issues: list[str] = []
    label = _txt(row.get("expected_warzone")) or f"row_{index}"
    prefix = f"{label}[{index}]"
    expected_warzone = _txt(row.get("expected_warzone"))

    if _txt(row.get("error")):
        issues.append(f"{prefix}: has error={_txt(row.get('error'))}")
        return issues

    status = _txt(row.get("status")).lower()
    if status != "completed":
        issues.append(f"{prefix}: status is not completed ({status})")

    report_tier = _txt(row.get("report_tier"))
    if report_tier not in VALID_TIERS:
        issues.append(f"{prefix}: invalid report_tier={report_tier}")

    pains = row.get("pain_titles")
    if not isinstance(pains, list) or len(pains) < 3:
        issues.append(f"{prefix}: pain_titles count < 3")
    else:
        seen_pains: set[str] = set()
        for pain in pains:
            title = _txt(pain)
            if _is_placeholder_pain(title):
                issues.append(f"{prefix}: placeholder pain title={title}")
            if title in seen_pains:
                issues.append(f"{prefix}: duplicate pain title={title}")
            seen_pains.add(title)
            if expected_warzone and _semantic_warzone_mismatch(
                expected_warzone=expected_warzone,
                text=title,
                classifier=classifier,
            ):
                issues.append(f"{prefix}: cross-warzone pain title={title}")

    opportunities = row.get("opportunity_titles")
    if not isinstance(opportunities, list) or len(opportunities) < 2:
        issues.append(f"{prefix}: opportunity_titles count < 2")
    else:
        seen_opps: set[str] = set()
        for title in opportunities:
            cleaned = _txt(title)
            if _is_low_signal_opportunity(cleaned):
                issues.append(f"{prefix}: low-signal opportunity title={cleaned}")
            if cleaned in seen_opps:
                issues.append(f"{prefix}: duplicate opportunity title={cleaned}")
            seen_opps.add(cleaned)
            if "围绕「围绕" in cleaned:
                issues.append(f"{prefix}: nested opportunity title={cleaned}")
            if expected_warzone and _semantic_warzone_mismatch(
                expected_warzone=expected_warzone,
                text=cleaned,
                classifier=classifier,
            ):
                issues.append(f"{prefix}: cross-warzone opportunity title={cleaned}")

    communities = row.get("community_titles")
    if not isinstance(communities, list) or not communities:
        issues.append(f"{prefix}: community_titles is empty")
    else:
        for name in communities:
            community = _txt(name)
            if not community.startswith("r/"):
                issues.append(f"{prefix}: invalid community title={community}")

    result_url = _txt(row.get("result_url"))
    if not result_url:
        issues.append(f"{prefix}: result_url missing")

    return issues


def validate_matrix(
    *,
    rows: list[dict[str, Any]],
    min_a_full: int | None,
    max_c_scouting: int | None,
) -> dict[str, Any]:
    classifier = _load_classifier()
    issues: list[str] = []
    for index, row in enumerate(rows):
        issues.extend(
            _validate_row(
                row,
                index,
                classifier=classifier,
            )
        )

    a_full = sum(1 for row in rows if _txt(row.get("report_tier")) == "A_full")
    b_trimmed = sum(1 for row in rows if _txt(row.get("report_tier")) == "B_trimmed")
    c_scouting = sum(1 for row in rows if _txt(row.get("report_tier")) == "C_scouting")

    if min_a_full is not None and a_full < min_a_full:
        issues.append(f"global: A_full count {a_full} < required {min_a_full}")
    if max_c_scouting is not None and c_scouting > max_c_scouting:
        issues.append(f"global: C_scouting count {c_scouting} > allowed {max_c_scouting}")

    return {
        "accepted": not issues,
        "total": len(rows),
        "a_full": a_full,
        "b_trimmed": b_trimmed,
        "c_scouting": c_scouting,
        "issues": issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate 8-warzone live matrix JSON contract")
    parser.add_argument("--input", required=True, help="Path to warzone_live_matrix_final_*.json")
    parser.add_argument("--min-a-full", type=int, default=None)
    parser.add_argument("--max-c-scouting", type=int, default=None)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"matrix file not found: {input_path}")

    rows = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise RuntimeError("matrix JSON must be a list")

    payload = validate_matrix(
        rows=[dict(row) for row in rows if isinstance(row, dict)],
        min_a_full=args.min_a_full,
        max_c_scouting=args.max_c_scouting,
    )
    payload["input"] = str(input_path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload["accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI utility
        print(f"validate_warzone_live_matrix failed: {exc}", file=sys.stderr)
        raise
