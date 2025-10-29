"""
测试报告导出服务
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.task import TaskStatus
from app.schemas.report_payload import (
    ReportContent,
    ReportExecutiveSummary,
    ReportMetadata,
    ReportOverview,
    ReportPayload,
    ReportStats,
    SentimentBreakdown,
    TopCommunity,
)
from app.services.report_export_service import ReportExportService


@pytest.fixture
def sample_report() -> ReportPayload:
    """创建示例报告数据"""
    task_id = uuid4()
    now = datetime.now(timezone.utc)

    return ReportPayload(
        task_id=task_id,
        status=TaskStatus.COMPLETED,
        generated_at=now,
        product_description="测试产品",
        report_html="<html><body><h1>测试报告</h1></body></html>",
        report=ReportContent(
            executive_summary=ReportExecutiveSummary(
                total_communities=5,
                key_insights=10,
                top_opportunity="测试机会",
            ),
            pain_points=[],
            competitors=[],
            opportunities=[],
            action_items=[],
            entity_summary={
                "brands": [{"name": "Notion", "mentions": 3}],
                "features": [{"name": "automation", "mentions": 2}],
                "pain_points": [],
            },
        ),
        metadata=ReportMetadata(
            analysis_version="1.0",
            confidence_score=0.85,
            processing_time_seconds=10.5,
            cache_hit_rate=0.8,
            total_mentions=100,
            recovery_applied=None,
            fallback_quality=None,
        ),
        overview=ReportOverview(
            sentiment=SentimentBreakdown(
                positive=60,
                neutral=30,
                negative=10,
            ),
            top_communities=[],
        ),
        stats=ReportStats(
            total_mentions=100,
            positive_mentions=60,
            negative_mentions=10,
            neutral_mentions=30,
        ),
    )


def test_generate_json(sample_report: ReportPayload) -> None:
    """测试 JSON 导出"""
    result = ReportExportService.generate_json(sample_report)

    assert isinstance(result, bytes)
    assert len(result) > 0

    # 验证可以解析为 JSON
    data = json.loads(result.decode("utf-8"))
    assert "task_id" in data
    assert "status" in data
    assert "report" in data


def test_generate_pdf_without_weasyprint(
    sample_report: ReportPayload, monkeypatch
) -> None:
    """测试没有 WeasyPrint 时的错误处理"""
    # 模拟 WeasyPrint 不可用
    import app.services.report_export_service as module

    monkeypatch.setattr(module, "WEASYPRINT_AVAILABLE", False)

    with pytest.raises(RuntimeError, match="WeasyPrint is not installed"):
        ReportExportService.generate_pdf(sample_report)


def test_generate_html_fallback(sample_report: ReportPayload) -> None:
    """测试 HTML 生成（备用方案）"""
    # 移除 report_html 以触发备用方案
    sample_report.report_html = None

    html = ReportExportService._generate_html(sample_report)

    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "测试产品" in html
    assert str(sample_report.task_id) in html
