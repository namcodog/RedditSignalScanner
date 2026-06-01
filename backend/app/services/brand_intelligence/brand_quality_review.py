from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, cast

from app.services.brand_intelligence.brand_quality_models import (
    BrandQualityItem,
    BrandQualityReport,
    BrandQualityRules,
    EvidenceThreshold,
    InterestTagRule,
)
from app.services.brand_intelligence.models import BrandCandidate, BrandDigestReport

CONFIG_ROOT = Path(__file__).resolve().parents[3] / "config"
DEFAULT_RULES_PATH = CONFIG_ROOT / "brand_quality_rules.json"
DEFAULT_TAGS_PATH = CONFIG_ROOT / "community_interest_tags.json"

__all__ = [
    "BrandQualityItem",
    "BrandQualityReport",
    "BrandQualityRules",
    "InterestTagRule",
    "build_brand_quality_review",
    "load_brand_quality_rules",
    "load_interest_tag_rules",
]


def load_brand_quality_rules(path: Path = DEFAULT_RULES_PATH) -> BrandQualityRules:
    payload = _load_json_object(path)
    thresholds = cast(dict[str, object], payload.get("verified_thresholds", {}))
    return BrandQualityRules(
        verified_thresholds={
            lifecycle: _threshold_from_payload(value)
            for lifecycle, value in thresholds.items()
            if isinstance(value, dict)
        },
        generic_terms=frozenset(
            _normalize(value)
            for value in _as_string_tuple(payload.get("generic_terms"))
        ),
        ambiguous_case_terms=frozenset(
            _normalize(value)
            for value in _as_string_tuple(payload.get("ambiguous_case_terms"))
        ),
        person_name_surnames=frozenset(
            _normalize(value)
            for value in _as_string_tuple(payload.get("person_name_surnames"))
        ),
    )


def load_interest_tag_rules(
    path: Path = DEFAULT_TAGS_PATH,
) -> tuple[InterestTagRule, ...]:
    payload = _load_json_object(path)
    tags = payload.get("tags", [])
    if not isinstance(tags, list):
        return ()
    rules: list[InterestTagRule] = []
    for item in tags:
        if not isinstance(item, dict):
            continue
        match = item.get("match", {})
        if not isinstance(match, dict):
            match = {}
        keywords = _as_string_tuple(match.get("keywords")) + _as_string_tuple(
            match.get("semantic_terms")
        )
        display_name = str(item.get("display_name") or "")
        if display_name and keywords:
            rules.append(InterestTagRule(display_name=display_name, keywords=keywords))
    return tuple(rules)


def build_brand_quality_review(
    digest: BrandDigestReport,
    *,
    rules: BrandQualityRules,
    tags: tuple[InterestTagRule, ...],
) -> BrandQualityReport:
    items = tuple(_review_brand(brand, rules, tags) for brand in digest.brands)
    return BrandQualityReport(
        report_date=digest.report_date, card_count=digest.card_count, items=items
    )


def _review_brand(
    brand: BrandCandidate,
    rules: BrandQualityRules,
    tags: tuple[InterestTagRule, ...],
) -> BrandQualityItem:
    noise_flags = _noise_flags(brand, rules)
    status = _review_status(brand, rules, noise_flags)
    interest_tags = _match_interest_tags(brand, tags)
    return BrandQualityItem(
        canonical_name=brand.canonical_name,
        review_status=status,
        source_lifecycle=brand.source_lifecycle,
        mention_count=len(brand.evidence),
        community_count=len(brand.communities),
        interest_tags=interest_tags,
        noise_flags=noise_flags,
        reason=_reason(brand, status, noise_flags),
    )


def _review_status(
    brand: BrandCandidate,
    rules: BrandQualityRules,
    noise_flags: tuple[str, ...],
) -> str:
    if (
        "generic_term" in noise_flags
        or "community_name_overlap" in noise_flags
        or "lowercase_ambiguous_match" in noise_flags
    ):
        return "rejected"
    threshold = rules.verified_thresholds.get(brand.source_lifecycle)
    if (
        threshold
        and len(brand.evidence) >= threshold.min_mentions
        and len(brand.communities) >= threshold.min_communities
    ):
        return "verified"
    return "candidate"


def _noise_flags(brand: BrandCandidate, rules: BrandQualityRules) -> tuple[str, ...]:
    flags: list[str] = []
    normalized = _normalize(brand.canonical_name)
    if normalized in rules.generic_terms:
        flags.append("generic_term")
    if normalized in rules.ambiguous_case_terms and not _has_exact_case_evidence(brand):
        flags.append("lowercase_ambiguous_match")
    if (
        brand.source_lifecycle == "candidate"
        and len(brand.evidence) <= 1
        and _looks_like_person_name(brand.canonical_name, rules)
    ):
        flags.append("person_name_shape")
    community_names = {
        _normalize(value.removeprefix("r/")) for value in brand.communities
    }
    if brand.source_lifecycle == "candidate" and normalized in community_names:
        flags.append("community_name_overlap")
    return tuple(flags)


def _match_interest_tags(
    brand: BrandCandidate,
    tags: tuple[InterestTagRule, ...],
) -> tuple[str, ...]:
    haystack = " ".join(
        [brand.canonical_name, *brand.communities, *brand.matched_terms]
    ).lower()
    matched = [
        rule.display_name
        for rule in tags
        if any(keyword.lower() in haystack for keyword in rule.keywords)
    ]
    return tuple(dict.fromkeys(matched))


def _reason(brand: BrandCandidate, status: str, noise_flags: tuple[str, ...]) -> str:
    if status == "rejected":
        return "命中噪音规则，不能进入品牌库。"
    if status == "verified":
        return "来源可信且证据达到当前阈值。"
    if noise_flags:
        return "有证据但存在噪音风险，先留在候选审核。"
    if brand.source_lifecycle == "candidate":
        return "来自历史候选池，需要人工确认后才能升级。"
    return "证据未达到验证阈值，继续观察。"


def _threshold_from_payload(value: Mapping[str, object]) -> EvidenceThreshold:
    return EvidenceThreshold(
        min_mentions=_as_int(value.get("min_mentions")),
        min_communities=_as_int(value.get("min_communities")),
    )


def _looks_like_person_name(value: str, rules: BrandQualityRules) -> bool:
    parts = value.strip().split()
    return (
        len(parts) == 2
        and all(re.match(r"^[A-Z][a-z]+$", part) for part in parts)
        and _normalize(parts[1]) in rules.person_name_surnames
    )


def _has_exact_case_evidence(brand: BrandCandidate) -> bool:
    pattern = re.compile(rf"\b{re.escape(brand.canonical_name)}\b")
    return any(pattern.search(item.source_text) for item in brand.evidence)


def _as_string_tuple(value: object) -> tuple[str, ...]:
    return (
        tuple(item for item in value if isinstance(item, str))
        if isinstance(value, list)
        else ()
    )


def _as_int(value: object) -> int:
    return int(value) if isinstance(value, int | str) else 0


def _load_json_object(path: Path) -> dict[str, object]:
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, object], payload) if isinstance(payload, dict) else {}


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
