from __future__ import annotations

from pathlib import Path

import csv

from backend.scripts.weekly_calibration import (
    CandidateRecord,
    ReviewDecision,
    apply_calibration_changes,
    select_review_samples,
)


def test_select_review_samples_stratified() -> None:
    candidates = [
        CandidateRecord(canonical="term_a", category="features", layer="L2", freq=120, score=5.0),
        CandidateRecord(canonical="term_b", category="features", layer="L2", freq=40, score=12.0),
        CandidateRecord(canonical="term_c", category="pain_points", layer="L3", freq=80, score=3.0),
        CandidateRecord(canonical="term_d", category="pain_points", layer="L3", freq=10, score=18.0),
    ]

    samples = select_review_samples(
        candidates,
        task_id="week-42",
        sample_rate=0.5,
        stratify=True,
    )

    picked = {row.canonical for row in samples}
    assert picked == {"term_a", "term_c"}
    assert all(row.task_id == "week-42" for row in samples)


def test_apply_calibration_changes(tmp_path: Path) -> None:
    lexicon = {
        "layers": {
            "L2": {
                "brands": [
                    {
                        "canonical": "Amazon",
                        "aliases": [],
                        "precision_tag": "exact",
                        "weight": 120.0,
                    }
                ]
            },
            "L3": {
                "features": [
                    {
                        "canonical": "checkout flow",
                        "aliases": [],
                        "precision_tag": "phrase",
                        "weight": 80.0,
                    }
                ]
            },
            "L4": {
                "pain_points": [
                    {
                        "canonical": "policy violation",
                        "aliases": [],
                        "precision_tag": "phrase",
                        "polarity": "negative",
                        "weight": 55.0,
                    }
                ]
            },
        }
    }

    exclude_file = tmp_path / "exclude.csv"
    exclude_file.write_text("term,reason,example_subreddit,added_date,layer\n", encoding="utf-8")

    decisions = [
        ReviewDecision(
            canonical="amz",
            category="brands",
            layer="L2",
            freq=100,
            score=5.0,
            risk_score=0.8,
            task_id="week-42",
            decision="merge",
            target="Amazon",
            notes="common shorthand",
        ),
        ReviewDecision(
            canonical="new tactic",
            category="features",
            layer="L3",
            freq=60,
            score=7.0,
            risk_score=0.7,
            task_id="week-42",
            decision="add",
            notes="shows up in L3",
        ),
        ReviewDecision(
            canonical="policy violation",
            category="pain_points",
            layer="L4",
            freq=20,
            score=2.0,
            risk_score=0.9,
            task_id="week-42",
            decision="delete",
            notes="false positive",
        ),
        ReviewDecision(
            canonical="spam phrase",
            category="features",
            layer="L1",
            freq=15,
            score=1.0,
            risk_score=0.95,
            task_id="week-42",
            decision="blacklist",
            notes="too generic",
        ),
    ]

    summary = apply_calibration_changes(
        lexicon,
        decisions,
        exclude_path=exclude_file,
        changelog_path=None,
        notes_path=None,
        task_id="week-42",
    )

    amazon_aliases = lexicon["layers"]["L2"]["brands"][0]["aliases"]
    assert "amz" in amazon_aliases

    new_features = [t["canonical"] for t in lexicon["layers"]["L3"]["features"]]
    assert "new tactic" in new_features

    pains = [t["canonical"] for t in lexicon["layers"]["L4"]["pain_points"]]
    assert "policy violation" not in pains

    with exclude_file.open() as fh:
        rows = list(csv.DictReader(fh))
    assert any(row["term"] == "spam phrase" for row in rows)

    assert summary["merge"] == 1
    assert summary["add"] == 1
    assert summary["delete"] == 1
    assert summary["blacklist"] == 1
