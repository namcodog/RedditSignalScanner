from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import cast

from app.services.brand_intelligence.archive_brand_pool_outputs import (
    render_archive_brand_pool_markdown,
    write_archive_brand_pool_outputs,
)
from app.services.brand_intelligence.archive_brand_pool_review import (
    build_archive_brand_pool_review,
)

SOURCE = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "services"
    / "brand_intelligence"
    / "archive_brand_pool_review.py"
)


def test_archive_brand_pool_dedupes_and_merges_domains(tmp_path: Path) -> None:
    _write_archive(tmp_path)

    report = build_archive_brand_pool_review(config_root=tmp_path)
    rows = {item.canonical_name: item for item in report.items}

    assert report.summary["raw_rows"] == 4
    assert report.summary["brand_count"] == 3
    assert rows["Acme Tool"].domains == ("Ecommerce", "Tools")
    assert rows["Brother"].review_status == "needs_review"
    assert rows["Plain Brand"].review_status == "ready_for_review"


def test_archive_brand_pool_writes_full_review_outputs(tmp_path: Path) -> None:
    _write_archive(tmp_path)
    report = build_archive_brand_pool_review(config_root=tmp_path)
    json_path = tmp_path / "pool.json"
    md_path = tmp_path / "pool.md"
    csv_path = tmp_path / "pool.csv"

    write_archive_brand_pool_outputs(
        report, json_path=json_path, md_path=md_path, csv_path=csv_path
    )

    payload = cast(dict[str, object], json.loads(json_path.read_text(encoding="utf-8")))
    rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8")))
    markdown = md_path.read_text(encoding="utf-8")
    assert cast(dict[str, object], payload["summary"])["db_writes"] is False
    assert len(rows) == 3
    assert "## Domain Summary" in markdown
    assert render_archive_brand_pool_markdown(report) == markdown


def test_archive_brand_pool_service_has_no_hardcoded_brand_list() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "Acme Tool" not in source
    assert "Plain Brand" not in source
    assert "Brother" not in source


def _write_archive(root: Path) -> None:
    archive = root / "semantic_sets" / "archive"
    archive.mkdir(parents=True)
    (archive / "brands_ecommerce.yml").write_text(
        "category: Ecommerce\nbrands:\n  - Acme Tool\n  - Brother\n",
        encoding="utf-8",
    )
    (archive / "brands_tools.yml").write_text(
        "category: Tools\nbrands:\n  - acme tool\n  - Plain Brand\n",
        encoding="utf-8",
    )
    (root / "brand_noise.yaml").write_text("general:\n  - brother\n", encoding="utf-8")
    hard_neg = root / "nlp" / "stopwords"
    hard_neg.mkdir(parents=True)
    (hard_neg / "hard_neg_brands.txt").write_text("", encoding="utf-8")
