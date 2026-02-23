# Phase 220

## 目标
- 补齐 Rant / Opportunity 报告模板与导出逻辑，按设计细化落地。

## 完成内容
- `export_markdown_report` 增加 Rant / Opportunity 专属段落（核心痛点、迁移意向、竞品分析、核心需求、现有工具、用户画像、市场机会、Top 发现帖）。
- 统一 Opportunity 强度计算复用，避免重复逻辑。
- 增加导出测试覆盖 Rant / Opportunity 关键段落。

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_report_export.py -q`

## 结论
- Phase 220 完成，Rant / Opportunity Markdown 结构已对齐设计并可导出。
