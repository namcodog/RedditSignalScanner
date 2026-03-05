from __future__ import annotations

from app.services.report.controlled_generator import render_report
from app.services.report.market_report import (
    MarketReportBuilder,
    CommunitySaturation,
    BrandSaturation,
    CopyAmmo,
)
from app.services.analysis.persona_generator import PersonaResult
from app.services.analysis.quote_extractor import QuoteResult


def test_market_report_builder_context_and_render() -> None:
    builder = MarketReportBuilder()
    analysis = {
        "insights": {
            "pain_points": [{"description": "订阅费太贵"}],
            "action_items": [{"id": "oppty-1", "problem_definition": "订阅费陷阱"}],
        },
        "sources": {"communities": ["r/homegym"], "posts_analyzed": 12},
    }

    personas = [
        PersonaResult(
            community="r/homegym",
            persona_label="DIY建设者",
            traits=["在乎性价比"],
            strategy="痛点切入",
            confidence=0.6,
            method="rules",
        )
    ]
    quotes = [
        QuoteResult(
            text="硬件已经很贵，为什么还要每月付费？",
            score=0.8,
            sentiment=-0.6,
            relevance=0.7,
            length=20,
            source="r/homegym",
        )
    ]
    saturation = [
        CommunitySaturation(
            community="r/homegym",
            brands=[BrandSaturation(brand="Tonal", saturation=0.8, status="高饱和")],
            overall_saturation=0.8,
        )
    ]
    copy_ammo = {"oppty-1": CopyAmmo(vs_subscription="每年多花$XXX不值", vs_competitor=None, pain_resonance="我们受够了订阅费", value_prop="一次性买断")}
    gtm_plans = {}

    ctx = builder.build_context(
        analysis=analysis,
        personas=personas,
        quotes=quotes,
        saturation=saturation,
        copy_ammo=copy_ammo,
        gtm_plans=gtm_plans,
    )

    tmpl = "# {title}\nPersona: {persona_list}\nQuote: {top_quote}"
    out = render_report(tmpl, ctx)

    assert "市场洞察报告 v1" in out
    assert "DIY建设者" in out or "DIY用户" in out

