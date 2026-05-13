from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from app.services.brand_intelligence.brand_quality_outputs import (
    render_brand_quality_review_markdown,
    write_brand_quality_review_outputs,
)
from app.services.brand_intelligence.brand_quality_review import (
    build_brand_quality_review,
    load_brand_quality_rules,
    load_interest_tag_rules,
)
from app.services.brand_intelligence.models import (
    BrandCandidate,
    BrandDigestReport,
    BrandEvidence,
)

SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "brand_intelligence"
    / "brand_quality_review.py"
)


def _evidence(text: str, community: str = "r/shopify") -> BrandEvidence:
    return BrandEvidence(
        card_id="card-1",
        community=community,
        source="quote",
        source_text=text,
        observed_at="2026-05-12T00:00:00Z",
    )


def _brand(
    name: str,
    lifecycle: str,
    evidence: list[BrandEvidence],
) -> BrandCandidate:
    candidate = BrandCandidate(name, source_lifecycle=lifecycle)
    candidate.evidence.extend(evidence)
    for item in evidence:
        candidate.communities.add(item.community)
    candidate.matched_terms.add(name)
    return candidate


def test_quality_review_assigns_status_without_promoting_archive_only_brands(
    tmp_path: Path,
) -> None:
    archive_evidence = [
        _evidence("Acme Tool appears in a seller discussion.", "r/ecommerce"),
        _evidence("Acme Tool also appears elsewhere.", "r/shopify"),
    ]
    digest = BrandDigestReport(
        report_date="2026-05-12",
        card_count=3,
        brands=(
            _brand("Amazon", "approved", [_evidence("Amazon changed fees.")]),
            _brand(
                "Shopify",
                "seed",
                [
                    _evidence("Shopify checkout."),
                    _evidence("Shopify seller ops.", "r/ecommerce"),
                ],
            ),
            _brand("Acme Tool", "candidate", archive_evidence),
        ),
    )

    report = build_brand_quality_review(
        digest,
        rules=load_brand_quality_rules(
            _write_rules(tmp_path, seed_mentions=2, generic_terms=())
        ),
        tags=load_interest_tag_rules(_write_tags(tmp_path)),
    )
    rows = {item.canonical_name: item for item in report.items}

    assert rows["Amazon"].review_status == "verified"
    assert rows["Shopify"].review_status == "verified"
    assert rows["Acme Tool"].review_status == "candidate"


def test_quality_review_maps_brands_to_user_interest_tags(tmp_path: Path) -> None:
    digest = BrandDigestReport(
        report_date="2026-05-12",
        card_count=1,
        brands=(
            _brand(
                "Shopify",
                "seed",
                [
                    _evidence(
                        "Shopify sellers discuss checkout conversion and inventory risk.",
                        "r/shopify",
                    )
                ],
            ),
        ),
    )

    report = build_brand_quality_review(
        digest,
        rules=load_brand_quality_rules(_write_rules(tmp_path)),
        tags=load_interest_tag_rules(_write_tags(tmp_path)),
    )

    assert report.items[0].interest_tags == ("卖家店铺运营",)
    assert report.summary["interest_tag_counts"] == {"卖家店铺运营": 1}


def test_quality_review_flags_noise_without_silent_acceptance(tmp_path: Path) -> None:
    digest = BrandDigestReport(
        report_date="2026-05-12",
        card_count=3,
        brands=(
            _brand("Case", "candidate", [_evidence("Case appears as a common word.")]),
            _brand(
                "John Smith", "candidate", [_evidence("John Smith wrote a comment.")]
            ),
            _brand(
                "SEO", "candidate", [_evidence("SEO is the community name.", "r/SEO")]
            ),
        ),
    )

    report = build_brand_quality_review(
        digest,
        rules=load_brand_quality_rules(_write_rules(tmp_path)),
        tags=load_interest_tag_rules(_write_tags(tmp_path)),
    )
    rows = {item.canonical_name: item for item in report.items}

    assert rows["Case"].review_status == "rejected"
    assert "generic_term" in rows["Case"].noise_flags
    assert rows["John Smith"].review_status == "candidate"
    assert "person_name_shape" in rows["John Smith"].noise_flags
    assert rows["SEO"].review_status == "rejected"
    assert "community_name_overlap" in rows["SEO"].noise_flags
    assert len(report.noise_items) == 3


def test_quality_review_writes_json_and_markdown(tmp_path: Path) -> None:
    digest = BrandDigestReport(
        report_date="2026-05-12",
        card_count=1,
        brands=(
            _brand("Shopify", "seed", [_evidence("Shopify checkout conversion.")]),
        ),
    )
    report = build_brand_quality_review(
        digest,
        rules=load_brand_quality_rules(_write_rules(tmp_path)),
        tags=load_interest_tag_rules(_write_tags(tmp_path)),
    )
    json_path = tmp_path / "quality.json"
    md_path = tmp_path / "quality.md"

    write_brand_quality_review_outputs(report, json_path=json_path, md_path=md_path)

    payload = cast(dict[str, object], json.loads(json_path.read_text(encoding="utf-8")))
    markdown = md_path.read_text(encoding="utf-8")
    assert cast(dict[str, object], payload["summary"])["db_writes"] is False
    assert "## Noise Audit" in markdown
    assert render_brand_quality_review_markdown(report) == markdown


def test_quality_review_service_has_no_hardcoded_brand_list() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "Shopify" not in source
    assert "Amazon" not in source
    assert "Acme Tool" not in source


def _write_rules(
    root: Path, *, seed_mentions: int = 1, generic_terms: tuple[str, ...] = ("case",)
) -> Path:
    path = root / "brand_quality_rules.json"
    path.write_text(
        json.dumps(
            {
                "verified_thresholds": {
                    "approved": {"min_mentions": 1, "min_communities": 1},
                    "seed": {"min_mentions": seed_mentions, "min_communities": 1},
                    "candidate": {"min_mentions": 99, "min_communities": 99},
                },
                "generic_terms": list(generic_terms),
                "person_name_surnames": ["smith"],
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_tags(root: Path) -> Path:
    path = root / "community_interest_tags.json"
    path.write_text(
        json.dumps(
            {
                "tags": [
                    {
                        "display_name": "卖家店铺运营",
                        "match": {"keywords": ["seller", "checkout", "shopify"]},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path
