# Phase 177 - 主系统口径统一（二次：需求打标/机会权重/趋势驱动）

## 目标
- 继续清理主系统硬编码口径，统一到配置或 DB。
- 按优先级落地：smart_tagger → opportunity_scorer → insights_enrichment。

## 变更摘要
- 需求打标词库配置化：新增 `backend/config/need_taxonomy.yaml`
- 需求词库加载器：新增 `backend/app/services/semantic/need_taxonomy.py`
- SmartTagger 改为读配置词库：`backend/app/services/semantic/smart_tagger.py`
- 机会权重配置化：`backend/config/scoring_rules.yaml` 增加 `need_weights` + `dual_label_bonus`
- ScoringRules 解析新增字段：`backend/app/services/analysis/scoring_rules.py`
- OpportunityScorer 读配置权重：`backend/app/services/analysis/opportunity_scorer.py`
- 趋势/驱动规则配置化：新增 `backend/config/insights_enrichment.yaml`
- InsightsEnrichment 读取配置：`backend/app/services/analysis/insights_enrichment.py`
- 迁移脚本新增 need_taxonomy：`backend/scripts/migrate_semantics.py`
- 新增测试：
  - `backend/tests/services/test_need_taxonomy.py`
  - `backend/tests/services/test_scoring_rules_need_weights.py`
  - `backend/tests/services/test_insights_enrichment_config.py`

## 测试（test 库）
- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test PYTHONPATH=backend pytest backend/tests/services/test_need_taxonomy.py backend/tests/services/test_scoring_rules_need_weights.py backend/tests/services/test_insights_enrichment_config.py -q`
- 结果：4 passed（pytest asyncio 配置告警不影响）

## 备注
- 若需让 need_taxonomy 生效到 DB：运行 `python -m backend.scripts.migrate_semantics`
