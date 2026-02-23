# Phase 21 - 后端黄金闭环“毕业证”（backend+DB）：回归测试 + 最小血缘写入 + 报告不被 sources 额外字段炸掉

日期：2025-12-16  
代码基线：`main@fbc5a89`（工作区 dirty；本阶段以当前代码实况为准）

## 一句话结论

把“后端黄金业务主线闭环”做成**可自动证明的回归测试**：登录拿 token → `/api/analyze` → pipeline 写库（tasks/analyses/reports）→ `/api/status` → `/api/report`；同时把最小血缘（社区数/评论数/配置哈希）写进 `Analysis.sources`，并修掉“sources 里多几个字段就把 /api/report 直接 500”的硬坑。

---

## 我查到的证据（以代码为准）

### 黄金主线入口与写库

- 创建任务入口：`backend/app/api/v1/endpoints/analyze.py:create_analysis_task`
- inline 执行 pipeline（test 环境）：`backend/app/api/v1/endpoints/analyze.py:_schedule_analysis` → `backend/app/tasks/analysis_task.py:execute_analysis_pipeline`
- 写库落点：`backend/app/tasks/analysis_task.py:_store_analysis_results`（写 `analyses` / `reports`，并把任务置为 completed）
- 状态查询：`backend/app/api/v1/endpoints/tasks.py:get_task_status`
- 报告查询：`backend/app/api/v1/endpoints/reports.py:get_analysis_report` → `backend/app/services/report_service.py:ReportService.get_report`

### DB 质量闸门（sources 必填）

- `Analysis.sources` 的 DB check constraint：`backend/alembic/versions/20251010_000001_initial_schema.py:validate_sources_schema`
  - 至少要求：`communities`（array）+ `posts_analyzed`（number）+ `cache_hit_rate`（number）

---

## 端到端链路（本期只覆盖 backend + DB）

用户注册/登录 → 拿 JWT token  
→ `POST /api/analyze`（创建 tasks）  
→（test 强制 inline）`execute_analysis_pipeline`  
→ `_store_analysis_results`（写 analyses/reports + tasks.completed）  
→ `GET /api/status/{task_id}`（缓存优先，必要时回源 DB）  
→ `GET /api/report/{task_id}`（ReportService 组装 payload 返回）

---

## 当前问题与根因（按模块归因）

### 1) 测试层：缺“毕业证”回归测试
- 问题：之前没有一条自动化测试能证明“token→analyze→写库→status→report”这条黄金链路一直能跑通。
- 根因：测试更多是“分段验证”，缺少“后端+DB闭环”总体验证。

### 2) 报告层：sources 多字段会把 /api/report 直接炸成 500
- 问题：`Analysis.sources` 里只要多几个字段（例如分析引擎写了 `ps_ratio/keywords/...`），`ReportService` 会因为严格 schema 校验直接报错，导致 `/api/report` 500。
- 根因：`ReportService._normalise_sources` 没做“白名单过滤”，而 `SourcesPayload` 又是 `extra=forbid`，导致额外字段触发 ValidationError。

### 3) 可追溯：sources 缺最小血缘字段（写不读）
- 问题：我们要的最小血缘（社区数/评论数/配置版本/哈希）没有稳定写进 `Analysis.sources`。
- 根因：写库阶段只透传 `result.sources`，没做统一兜底补齐。

---

## 方案（保守版 / 升级版）

### 保守版（本期落地，最小改动、最快稳定）
- 新增“后端+DB黄金闭环回归测试”，把主线跑通变成可验证契约：`backend/tests/api/test_golden_business_flow.py`
- 写库时补齐最小血缘字段（不改表结构，只写 JSON）：`backend/app/tasks/analysis_task.py:_store_analysis_results`
  - `communities_count`
  - `comments_analyzed`（缺省为 0，先写不读）
  - `crawler_config_sha256`（基于 `config/crawler.yml`/`backend/config/crawler.yml` 的 sha256）
- 报告服务对 sources 做白名单过滤：`backend/app/services/report_service.py:ReportService._normalise_sources`
  - 额外字段保留在 DB，但报告生成只取 schema 允许的字段，避免 500

### 升级版（后续再做）
- 让 `comments_analyzed` 来自真实采集/清洗统计（而不是缺省 0）
- 把“配置版本”扩展到更多关键 YAML（scoring_rules、lexicon 等）并形成统一版本标识

---

## 风险与回滚

- 风险：`Analysis.sources` 增加字段是 JSON 扩展，不影响 DB schema，但如果下游有人“强依赖全量 sources”，需要确认读取方是否只取自己需要的字段。
- 回滚：
  - 若需要回退最小血缘：删掉 `analysis_task.py:_store_analysis_results` 里对 sources 的补齐逻辑即可（不会影响历史数据）。
  - 若需要回退 sources 白名单过滤：恢复 `ReportService._normalise_sources` 原逻辑即可（但会重新暴露 500 风险）。

---

## 测试与监控（必须包含）

### 新增/更新测试

- ✅ 后端黄金闭环回归测试：`backend/tests/api/test_golden_business_flow.py`
- ✅ 报告可用性（sources 扩展字段不应导致 500）：`backend/tests/api/test_reports.py::test_get_report_tolerates_extended_sources_payload`

### 本地验证命令（示例）

- `cd backend && APP_ENV=test ENABLE_CELERY_DISPATCH=0 SKIP_DB_RESET=1 pytest -q tests/api/test_golden_business_flow.py`
- `cd backend && APP_ENV=test ENABLE_CELERY_DISPATCH=0 SKIP_DB_RESET=1 pytest -q tests/api/test_reports.py::test_get_report_tolerates_extended_sources_payload`

---

## 验收标准（可量化）

1) 回归测试可证明黄金闭环：`test_golden_business_flow_persists_task_analysis_and_report` 通过。  
2) 写库后 `Analysis.sources` 至少包含：`communities/posts_analyzed/cache_hit_rate`（DB 闸门）+ `communities_count/comments_analyzed/crawler_config_sha256`（最小血缘）。  
3) `Analysis.sources` 即使包含额外字段（ps_ratio/keywords/...），`GET /api/report/{task_id}` 仍返回 200（不再 500）。  

