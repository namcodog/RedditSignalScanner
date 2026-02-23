# Phase 218

## 目标
- 生成增强版 Markdown 报告，并在响应中提供 markdown_report。

## 变更
- 新增导出模块：`backend/app/services/hotpost/report_export.py`
- 搜索响应补充 markdown_report：`backend/app/services/hotpost/service.py`
- Schema/前端类型补齐：`backend/app/schemas/hotpost.py`, `frontend/src/types/hotpost.ts`
- 独立导出脚本：`backend/scripts/export_hotpost_report.py`

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_report_export.py -q`

## 产物
- 示例报告：`reports/2026-02-02-增强版报告示例.md`

## 结论
- Phase 218 完成，Markdown 导出与示例已生成。
