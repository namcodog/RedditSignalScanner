from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from app.services.brand_intelligence.brand_digest import build_brand_digest_from_catalog
from app.services.brand_intelligence.source_catalog import (
    load_brand_source_catalog,
    render_brand_source_catalog_markdown,
    write_brand_source_catalog_outputs,
)

SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "brand_intelligence"
    / "source_catalog.py"
)


def _write_fixture_config(root: Path) -> None:
    (root / "semantic_sets" / "archive").mkdir(parents=True)
    (root / "entity_dictionary").mkdir()
    (root / "nlp" / "stopwords").mkdir(parents=True)
    (root / "semantic_sets" / "unified_lexicon.yml").write_text(
        """
version: 1
themes:
  test:
    brands:
      - Amazon
    aliases:
      Amazon: ["AMZ"]
""".strip(),
        encoding="utf-8",
    )
    (root / "entity_dictionary" / "brands_base.csv").write_text(
        "canonical,category\nshopify,brands\namazon,brands\n",
        encoding="utf-8",
    )
    (root / "semantic_sets" / "archive" / "brands_tools.yml").write_text(
        """
category: Tools
brands:
  - Acme Tool
  - Generic
""".strip(),
        encoding="utf-8",
    )
    (root / "brand_noise.yaml").write_text(
        """
general:
  - Generic
""".strip(),
        encoding="utf-8",
    )
    (root / "nlp" / "stopwords" / "hard_neg_brands.txt").write_text(
        "IgnoreMe\n",
        encoding="utf-8",
    )


def test_source_catalog_merges_sources_and_applies_lifecycle_priority(
    tmp_path: Path,
) -> None:
    _write_fixture_config(tmp_path)

    catalog = load_brand_source_catalog(config_root=tmp_path)
    source_counts = cast(dict[str, object], catalog.summary["source_counts"])
    noise_overlaps = cast(list[str], catalog.summary["noise_overlaps"])

    assert catalog.get("amazon").lifecycle == "approved"
    assert catalog.get("shopify").lifecycle == "seed"
    assert catalog.get("Acme Tool").lifecycle == "candidate"
    assert catalog.get("Generic").lifecycle == "rejected"
    assert catalog.get("IgnoreMe").lifecycle == "rejected"
    assert source_counts["unified_lexicon"] == 1
    assert source_counts["brands_base"] == 2
    assert source_counts["archive"] == 2
    assert "generic" in noise_overlaps


def test_digest_uses_catalog_and_keeps_archive_hits_as_candidates(
    tmp_path: Path,
) -> None:
    _write_fixture_config(tmp_path)
    catalog = load_brand_source_catalog(config_root=tmp_path)

    report = build_brand_digest_from_catalog(
        [
            {
                "card_id": "card-1",
                "title": "Shopify teams compare AMZ and Acme Tool",
                "summary_line": "Generic is a noise word here.",
                "top_community": "r/shopify",
                "published_at": "2026-05-12T01:00:00Z",
            }
        ],
        catalog=catalog,
        report_date="2026-05-12",
    )
    payload = report.to_payload()
    brand_rows = cast(list[dict[str, object]], payload["brands"])
    brands = {str(item["canonical_name"]): item for item in brand_rows}

    assert brands["Amazon"]["source_lifecycle"] == "approved"
    assert brands["shopify"]["source_lifecycle"] == "seed"
    assert brands["Acme Tool"]["source_lifecycle"] == "candidate"
    assert "Generic" not in brands


def test_source_catalog_writes_audit_outputs(tmp_path: Path) -> None:
    _write_fixture_config(tmp_path)
    catalog = load_brand_source_catalog(config_root=tmp_path)
    json_path = tmp_path / "catalog.json"
    md_path = tmp_path / "catalog.md"

    write_brand_source_catalog_outputs(catalog, json_path=json_path, md_path=md_path)

    payload = cast(dict[str, object], json.loads(json_path.read_text(encoding="utf-8")))
    summary = cast(dict[str, object], payload["summary"])
    markdown = md_path.read_text(encoding="utf-8")
    assert summary["total_entries"] == 5
    assert "| approved | 1 |" in markdown
    assert render_brand_source_catalog_markdown(catalog) == markdown


def test_source_catalog_has_no_hardcoded_brand_list() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "Shopify" not in source
    assert "Amazon" not in source
    assert "Acme Tool" not in source
