# Phase 115 - PRD vs 运行入口 全量走查清单

日期：2026-01-19

## 目标
用“运行入口”反向核对 PRD，确保每个模块都有可执行入口（命令/URL/API/定时任务/脚本），能对得上即可。

## 走查范围
- PRD-SYSTEM + PRD-01~PRD-10
- 运行入口来源：`Makefile`/`makefiles/*`、`docs/本地启动指南.md`、`docs/OPERATIONS.md`、`docs/API-REFERENCE.md`、`frontend/src/router/index.tsx`、`backend/app/core/celery_app.py`

## 全量走查清单（PRD -> 运行入口）

### A. 系统运行入口（PRD-SYSTEM 3/5/8）
- [ ] 一键黄金路径：`make dev-golden-path`（来源：`makefiles/dev.mk`、`docs/本地启动指南.md`）
- [ ] 后端启动：`make dev-backend` / `uvicorn app.main:app --reload --port 8006`（`makefiles/dev.mk`、`scripts/makefile-common.sh`、`README.md`）
- [ ] 前端启动：`make dev-frontend` / `npm run dev -- --port 3006`（`makefiles/dev.mk`、`docs/本地启动指南.md`）
- [ ] Celery Worker：`make celery-start`（`makefiles/celery.mk`）
- [ ] Celery Beat：`make dev-celery-beat`（`makefiles/celery.mk`）
- [ ] 服务重启/清理：`make restart-backend`/`make restart-frontend`/`make kill-ports`（`makefiles/ops.mk`、`makefiles/infra.mk`）

### B. 健康/诊断入口（PRD-SYSTEM 9/10）
- [ ] 健康检查：`GET /api/healthz`（`docs/API-REFERENCE.md`、`docs/本地启动指南.md`）
- [ ] 运行时诊断：`GET /api/tasks/diag`、`GET /api/diag/runtime`（`docs/API-REFERENCE.md`）
- [ ] 任务队列统计：`GET /api/tasks/stats`（`docs/API-REFERENCE.md`）
- [ ] Redis/Celery 运维入口：`redis-cli ping`、`celery inspect active`（`docs/OPERATIONS.md`）
- [ ] API 真相源：`GET /openapi.json`（`docs/API-REFERENCE.md`）

### C. 数据模型入口（PRD-01）
- [ ] Schema 真相：`docs/sop/2025-12-14-database-architecture-atlas.md` + `current_schema.sql`（PRD-SYSTEM 0）
- [ ] 迁移入口：`make db-upgrade` / `make db-downgrade` / `make db-migrate`（`makefiles/db.mk`）

### D. 用户前端入口（PRD-05）
- [ ] 首页：`/`
- [ ] 进度页：`/progress/:taskId`
- [ ] 报告页：`/report/:taskId`
- [ ] 洞察页：`/insights/:taskId`
- [ ] 决策单元页：`/decision-units`
- [ ] 登录/注册：`/login`、`/register`
（来源：`frontend/src/router/index.tsx`）

### E. 用户链路 API 入口（PRD-02/03/11）
- [ ] 认证：`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me`
- [ ] 任务创建：`POST /api/analyze`
- [ ] 进度：`GET /api/analyze/stream/{task_id}`（SSE）/ `GET /api/status/{task_id}`（轮询兜底）
- [ ] 报告：`GET /api/report/{task_id}`
- [ ] 质量账本：`GET /api/tasks/{task_id}/sources`
- [ ] DecisionUnit：`GET /api/decision-units` / `GET /api/decision-units/{id}` / `POST /api/decision-units/{id}/feedback`
- [ ] Beta 反馈：`POST /api/beta/feedback`
- [ ] 输入指导：`GET /api/guidance/input`
- [ ] 洞察卡片：`GET /api/insights/{task_id}` / `GET /api/insights/card/{insight_id}`
- [ ] 质量指标：`GET /api/metrics`、`GET /api/metrics/daily`
- [ ] 导出：`GET /api/report/{task_id}/download`、`GET /api/report/{task_id}/entities/download`、`GET /api/report/{task_id}/communities/download`、`POST /api/export/csv`
- [ ] 路径别名：`/api/v1` 为影子门牌（不建议前端同时支持两套）
（来源：`docs/API-REFERENCE.md`）

### F. Admin 前端入口（PRD-07/10）
- [ ] Admin 入口：`/admin`
- [ ] 社区池：`/admin/communities/pool`
- [ ] 导入页：`/admin/communities/import`
- [ ] 任务账本：`/admin/tasks/ledger`
- [ ] 指标面板：`/dashboard`
（来源：`frontend/src/router/index.tsx`）

### G. Admin API 入口（PRD-07/09/10）
- [ ] 社区池/发现/调级：`/api/admin/communities/*`
- [ ] 调级建议与 DecisionUnit：`/api/admin/communities/tier-suggestions`、`/emit-decision-units`
- [ ] Excel 导入：`/api/admin/communities/template`、`/import`、`/import-history`
- [ ] 任务复盘：`/api/admin/tasks/{task_id}/ledger`、`/api/admin/tasks/recent`
- [ ] facts 审计：`/api/admin/facts/tasks/{task_id}/latest`、`/api/admin/facts/snapshots/{snapshot_id}`
- [ ] 监控指标：`/api/admin/metrics/contract-health`、`/api/admin/metrics/routes`、`/api/admin/metrics/semantic`
- [ ] 语义候选：`/api/admin/semantic-candidates/*`
（来源：`docs/API-REFERENCE.md`）

### H. 任务/调度入口（PRD-04）
- [ ] 队列入口：`analysis_queue`、`patrol_queue`、`backfill_queue`、`backfill_posts_queue_v2`、`probe_queue`、`compensation_queue`、`maintenance_queue`、`cleanup_queue`、`crawler_queue`、`monitoring_queue`
- [ ] Beat 任务（核心心跳）：`tick-tiered-crawl` → `tasks.crawler.crawl_seed_communities_incremental`
- [ ] Beat 任务（低质巡航/回填/调度）：`crawl-low-quality-communities`、`plan_backfill_bootstrap`、`plan_seed_sampling`、`dispatch_task_outbox`
- [ ] Beat 任务（指标/监控）：`generate-daily-metrics`、`monitor-crawler-health`、`monitor-contract-health`
- [ ] Beat 任务（调级与决策单元）：`generate-daily-tier-suggestions`、`emit-daily-tier-suggestion-decision-units`
- [ ] Probe 入口：`probe-hot-12h`（可选开关）
（来源：`backend/app/core/celery_app.py`）

### I. 抓取/清洗入口（PRD-04/09/PRD-SYSTEM 8.4/8.5）
- [ ] 抓取 SOP 真相：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
- [ ] 清洗打分 SOP 真相：`docs/sop/数据清洗打分规则v1.2规范.md`
- [ ] 配置入口：`backend/config/crawler.yml`、`backend/config/deduplication.yaml`、`backend/config/community_blacklist.yaml`、`backend/config/probe_hot_sources.yaml`
- [ ] 手动触发入口：`make crawl-once`、`make crawl-crossborder`、`make crawl-seeds`（`makefiles/dev.mk`）

### J. 语义库闭环入口（PRD-SYSTEM 8.6）
- [ ] 语义库配置：`backend/config/semantic_sets/*`（含 crossborder_v2.* / unified_lexicon.yml）
- [ ] 实体词典：`backend/config/entity_dictionary/*`（含 crossborder_v2.csv）
- [ ] 语义抽取脚本：`backend/scripts/extract_lexicon_from_corpus.py`、`backend/scripts/semantic_lexicon_build.py`
- [ ] 语义候选审核入口：`/api/admin/semantic-candidates/*`

### K. 导出与反馈入口（PRD-SYSTEM 11）
- [ ] 报告下载：`GET /api/report/{task_id}/download`
- [ ] 社区列表导出：`GET /api/report/{task_id}/communities/download`
- [ ] 实体导出：`GET /api/report/{task_id}/entities/download`
- [ ] CSV 导出：`POST /api/export/csv`
- [ ] DecisionUnit 反馈：`POST /api/decision-units/{id}/feedback`

### L. 测试/演练入口（PRD-08/PRD-SYSTEM 9.6）
- [ ] 端到端测试：`make test-e2e` / `make test-admin-e2e`
- [ ] API 契约测试：`make test-contract`
- [ ] 故障注入测试：`backend/tests/e2e/test_fault_injection.py`
- [ ] 演练矩阵：`scripts/phase106_rehearsal_matrix.py` + `scripts/phase106_rehearsal_matrix.sample.json`

## 结论
运行入口与 PRD 模块已逐项对齐；API 细节以 `GET /openapi.json` 与 `docs/API-REFERENCE.md` 为准。
