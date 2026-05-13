# Phase 154 - Backend report payload enrichments

## 变更
- 新增 report payload 字段: pain_points/opportunities title/text, market_health, purchase_drivers
- action_items 增补 title/category, 且在处理流程中保持字段不丢失
- market_health.ps_ratio 口径：facts_slice 优先、sources.ps_ratio 兜底
- API 文档同步口径（docs/API-REFERENCE.md）
- PRD 口径同步：PRD-02, PRD-03, PRD-05, PRD-SYSTEM
- PRD 口径同步：PRD-INDEX, PRD-08

## 测试
- pytest backend/tests/services/test_report_service.py -k "populates_titles_and_market_health"
- pytest backend/tests/services/test_report_service.py -k "market_health_ps_ratio_fallback_to_sources"

## 备注
- 测试日志中出现 OpenAI 401 警告(不影响测试通过), 与本次逻辑无关
