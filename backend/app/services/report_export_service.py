"""
报告导出服务

提供 PDF、JSON 等格式的报告导出功能。
"""
from __future__ import annotations

import json
from io import BytesIO
from typing import Literal

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from app.schemas.report_payload import ReportPayload


ExportFormat = Literal["pdf", "json"]


class ReportExportService:
    """报告导出服务，支持多种格式导出"""

    @staticmethod
    def generate_pdf(report: ReportPayload) -> bytes:
        """
        将报告转换为 PDF 格式
        
        Args:
            report: 报告数据
            
        Returns:
            PDF 文件的字节内容
            
        Raises:
            RuntimeError: 如果 WeasyPrint 未安装
        """
        if not WEASYPRINT_AVAILABLE:
            raise RuntimeError(
                "WeasyPrint is not installed. "
                "Install it with: pip install weasyprint"
            )
        
        # 如果报告已有 HTML 内容，直接使用
        if report.report_html:
            html_content = report.report_html
        else:
            # 否则生成简单的 HTML
            html_content = ReportExportService._generate_html(report)
        
        # 转换为 PDF
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()

    @staticmethod
    def generate_json(report: ReportPayload) -> bytes:
        """
        将报告转换为 JSON 格式
        
        Args:
            report: 报告数据
            
        Returns:
            JSON 文件的字节内容
        """
        # 使用 Pydantic 的 model_dump 确保类型安全
        data = report.model_dump(mode="json")
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        return json_str.encode("utf-8")

    @staticmethod
    def _generate_html(report: ReportPayload) -> str:
        """
        生成简单的 HTML 报告（备用方案）
        
        Args:
            report: 报告数据
            
        Returns:
            HTML 字符串
        """
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Signal Scanner - 分析报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{ color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px; }}
        h2 {{ color: #1e40af; margin-top: 30px; }}
        .metadata {{ background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .section {{ margin: 20px 0; }}
        .item {{ margin: 15px 0; padding: 10px; border-left: 3px solid #2563eb; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center; color: #6b7280; }}
    </style>
</head>
<body>
    <h1>Reddit Signal Scanner - 分析报告</h1>
    
    <div class="metadata">
        <p><strong>任务ID:</strong> {report.task_id}</p>
        <p><strong>生成时间:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>产品描述:</strong> {report.product_description or 'N/A'}</p>
    </div>

    <div class="section">
        <h2>概览</h2>
        <p><strong>分析社区数:</strong> {len(report.overview.top_communities)}</p>
        <p><strong>总提及数:</strong> {report.stats.total_mentions}</p>
        <p><strong>正面提及:</strong> {report.stats.positive_mentions} | <strong>负面提及:</strong> {report.stats.negative_mentions} | <strong>中性提及:</strong> {report.stats.neutral_mentions}</p>
    </div>

    <div class="section">
        <h2>痛点分析</h2>
        {''.join(f'<div class="item"><strong>{p.title}</strong><br>{p.description}</div>' for p in report.report.pain_points)}
    </div>

    <div class="section">
        <h2>竞品分析</h2>
        {''.join(f'<div class="item"><strong>{c.name}</strong><br>{c.description}</div>' for c in report.report.competitors)}
    </div>

    <div class="section">
        <h2>机会点</h2>
        {''.join(f'<div class="item"><strong>{o.title}</strong><br>{o.description}</div>' for o in report.report.opportunities)}
    </div>

    <div class="footer">
        <p>由 Reddit Signal Scanner 生成 | {report.generated_at.strftime('%Y-%m-%d')}</p>
    </div>
</body>
</html>
"""
        return html


__all__ = ["ReportExportService", "ExportFormat"]

