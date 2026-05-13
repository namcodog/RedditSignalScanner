from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "community_value_scoring.json"

STAGE_ALREADY = "already_in_pool"
STAGE_OBSERVE = "observe"
STAGE_TESTING = "testing"
STAGE_VALIDATED = "validated"
STAGE_POOL_CANDIDATE = "pool_candidate"
STAGE_REJECT = "reject"


def load_value_scoring_rules(path: Path = CONFIG_PATH) -> dict[str, dict[str, int]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("community value scoring config must be an object")
    return {
        "weights": _int_section(raw, "weights"),
        "penalties": _int_section(raw, "penalties"),
        "thresholds": _int_section(raw, "thresholds"),
    }


def assess_community_value(
    *,
    evidence: Mapping[str, int],
    has_tags: bool,
    in_pool: bool,
    feedback_action: str,
    new_topic_count: int,
    rules: Mapping[str, Mapping[str, int]] | None = None,
) -> dict[str, object]:
    scoring_rules = rules or load_value_scoring_rules()
    score = _score(
        evidence=evidence,
        has_tags=has_tags,
        new_topic_count=new_topic_count,
        weights=scoring_rules["weights"],
        penalties=scoring_rules["penalties"],
    )
    return {
        "score": score,
        "stage": _stage(
            evidence=evidence,
            score=score,
            in_pool=in_pool,
            feedback_action=feedback_action,
            thresholds=scoring_rules["thresholds"],
        ),
        "positive_signals": _positive_signals(evidence, has_tags=has_tags, new_topic_count=new_topic_count),
        "risks": _value_risks(evidence, has_tags=has_tags),
    }


def _score(
    *,
    evidence: Mapping[str, int],
    has_tags: bool,
    new_topic_count: int,
    weights: Mapping[str, int],
    penalties: Mapping[str, int],
) -> int:
    if evidence["total_evidence"] <= 0:
        return 0
    raw = (
        evidence["candidate_count"] * weights["candidate"]
        + evidence["draft_count"] * weights["draft"]
        + evidence["published_count"] * weights["published"]
        + min(new_topic_count, 3) * weights["new_topic"]
        - evidence["duplicate_count"] * penalties["duplicate"]
        - evidence["reject_count"] * penalties["reject"]
    )
    raw += weights["tag_mapping"] if has_tags else -penalties["missing_tag"]
    return max(0, min(100, raw))


def _stage(
    *,
    evidence: Mapping[str, int],
    score: int,
    in_pool: bool,
    feedback_action: str,
    thresholds: Mapping[str, int],
) -> str:
    if in_pool:
        return STAGE_ALREADY
    if feedback_action == STAGE_REJECT:
        return STAGE_REJECT
    if evidence["total_evidence"] <= 0:
        return STAGE_OBSERVE
    if evidence["published_count"] >= 2 and score >= thresholds["pool_candidate_min"]:
        return STAGE_POOL_CANDIDATE
    if evidence["published_count"] > 0 or score >= thresholds["validated_min"]:
        return STAGE_VALIDATED
    return STAGE_TESTING


def _positive_signals(evidence: Mapping[str, int], *, has_tags: bool, new_topic_count: int) -> list[str]:
    signals: list[str] = []
    if evidence["candidate_count"] > 0:
        signals.append("candidate_evidence")
    if evidence["draft_count"] > 0:
        signals.append("draft_evidence")
    if evidence["published_count"] > 0:
        signals.append("published_evidence")
    if has_tags:
        signals.append("interest_tag_mapping")
    if new_topic_count > 0:
        signals.append("new_topic_coverage")
    return signals


def _value_risks(evidence: Mapping[str, int], *, has_tags: bool) -> list[str]:
    risks: list[str] = []
    if evidence["duplicate_count"] > 0:
        risks.append("duplicate_posts")
    if evidence["reject_count"] > 0:
        risks.append("review_rejections")
    if evidence["total_evidence"] > 0 and not has_tags:
        risks.append("no_interest_tag_mapping")
    return risks


def _int_section(raw: Mapping[str, object], name: str) -> dict[str, int]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"community value scoring config missing {name}")
    return {str(key): _int(item) for key, item in value.items()}


def _int(value: object) -> int:
    if isinstance(value, int | float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(value)
    raise ValueError("community value scoring config values must be numbers")


__all__ = ["assess_community_value", "load_value_scoring_rules"]
