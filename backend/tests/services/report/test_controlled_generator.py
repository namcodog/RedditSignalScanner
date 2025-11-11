from __future__ import annotations

from pathlib import Path

from backend.app.services.report.controlled_generator import (
    build_context,
    render_report,
    validate_report_structure,
)


def test_render_report_uses_analysis_and_lexicon(tmp_path: Path) -> None:
    analysis = {
        "insights": {
            "pain_points": [
                {
                    "description": "Account suspension",
                    "frequency": 42,
                    "severity": "high",
                    "example_posts": [
                        {
                            "community": "r/AmazonSeller",
                            "content": "My account was banned overnight",
                        }
                    ],
                }
            ],
            "pain_clusters": [
                {"topic": "L1 cluster", "samples": ["Sellers struggle with baseline tooling."]}
            ],
            "competitor_layers_summary": [
                {
                    "layer": "L2",
                    "label": "平台层",
                    "top_competitors": [
                        {"name": "Amazon", "mentions": 120},
                        {"name": "Shopify", "mentions": 90},
                    ],
                    "threats": "Listing policy churn",
                },
                {
                    "layer": "L3",
                    "label": "执行层",
                    "top_competitors": [
                        {"name": "TikTok Ads", "mentions": 60},
                    ],
                    "threats": "Creative iteration cost",
                },
            ],
            "channel_breakdown": [
                {"name": "TikTok Ads", "mentions": 300},
                {"name": "Email", "mentions": 200},
            ],
            "action_items": [
                {
                    "problem_definition": "Account suspension risk",
                    "evidence_chain": [
                        {
                            "title": "Seller lost account",
                            "note": "r/AmazonSeller",
                        }
                    ],
                    "suggested_actions": ["Audit compliance playbook"],
                }
            ],
        },
        "sources": {
            "communities": ["r/AmazonSeller", "r/Shopify"],
        },
    }

    lexicon = {
        "layers": {
            "L1": {
                "features": [
                    {"canonical": "checkout", "weight": 10},
                    {"canonical": "conversion", "weight": 8},
                ]
            },
            "L2": {
                "pain_points": [
                    {"canonical": "policy violation", "weight": 12},
                    {"canonical": "refund dispute", "weight": 11},
                ]
            },
            "L3": {
                "features": [
                    {"canonical": "creative testing", "weight": 9},
                    {"canonical": "retargeting", "weight": 7},
                ]
            },
        }
    }

    metrics = {
        "entity_coverage": {
            "overall": 0.84,
            "pain_points": 0.51,
            "brands": 0.62,
            "top10_unique_share": 0.73,
        },
        "layer_coverage": [
            {"layer": "L1", "coverage": 0.91},
            {"layer": "L2", "coverage": 0.87},
            {"layer": "L3", "coverage": 0.8},
            {"layer": "L4", "coverage": 0.7},
        ],
    }

    context, evidence = build_context(analysis, lexicon, metrics, task_id="task-123")
    assert "Account suspension" in context["L4_pain_1"]
    assert context["L1_terms"].startswith("checkout")
    assert evidence

    template = "Task {task_id}\nL4: {L4_pain_1} [{L4_pain_1_ids}]\nEvidence:\n{evidence_table}"
    output = render_report(template, context)
    assert "task-123" in output
    assert "EV-L4" in output
    assert "Evidence:" in output


def test_validate_report_structure() -> None:
    report_a = """## A\n### B\ncontent"""
    report_b = """## A\n### B\nother"""
    report_c = """## A\n### C\ncontent"""

    assert validate_report_structure(report_a, report_b)
    assert not validate_report_structure(report_a, report_c)
