# PRD-SYSTEM: Reddit Signal Scanner（系统级 PRD，唯一标准）

**版本日期**：2026-01-19  
**范围**：覆盖全系统（后端 + 前端 + Admin + 任务系统 + 数据模型 + 运维）  
**唯一标准**：本文件为系统级 PRD；模块 PRD 为细化说明，必须与本文件一致。  

---

## 0. 对齐口径（真相源）
- **API 真相**：`docs/API-REFERENCE.md`（已同步至本文件）
- **数据库真相**：`docs/sop/2025-12-14-database-architecture-atlas.md` + `current_schema.sql`  
  （`docs/archive/2025-12-14-database-architecture-atlas.md` 为历史副本，不作为真相）
- **抓取真相**：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
- **清洗/打分真相**：`docs/sop/数据清洗打分规则v1.2规范.md`
- **语义库/闭环真相**：`.specify/specs/011-semantic-lexicon-development-plan.md`、`.specify/specs/016-unified-semantic-report-loop/spec.md`、`.specify/specs/016-unified-semantic-report-loop/design.md`、`docs/semantic-library-guide.md`
- **演练与故障注入**：`scripts/phase106_rehearsal_matrix.py`、`backend/tests/e2e/test_fault_injection.py`
- **执行记录**：`reports/phase-log/phase106.md`、`reports/phase-log/phase107.md`、`reports/phase-log/phase108.md`、`reports/phase-log/phase109.md`、`reports/phase-log/phase110.md`、`reports/phase-log/phase111.md`、`reports/phase-log/phase112.md`、`reports/phase-log/phase113.md`、`reports/phase-log/phase114.md`
- **启动与运维**：`docs/本地启动指南.md`、`docs/OPERATIONS.md`

**规则**：新增能力必须先更新 PRD，再改实现；若实现与 PRD 冲突，以 PRD 为准并回滚实现或修文档。

---

## 1. 产品目标与用户角色

### 1.1 核心承诺
- 30 秒输入，5 分钟分析，输出可用报告。
- 结果必须可解释：料不够要给出原因与下一步动作。

### 1.2 角色
- **普通用户**：提交分析、查看报告、反馈 Beta、查看 DecisionUnit。
- **Admin**：社区池管理、调级建议、导入、任务复盘账本、合同健康度指标、语义候选审核。

---

## 2. 系统边界

### 2.1 系统内包含
- Reddit 数据采集与缓存
- 分析引擎（痛点/竞品/机会）
- facts_v2 质量门禁与可追溯账本
- LLM 报告生成（insights 主线 + facts_v2 证据切片）+ 导出
- DecisionUnit 产出与反馈闭环
- Admin 运维与社区池管理

### 2.2 系统外不做
- WebSocket 双向实时协作
- 复杂 BI 可视化面板
- 多任务并行管理 UI（用户侧）

---

## 3. 高层架构

### 3.1 架构组件
- **后端**：FastAPI + SQLAlchemy + Celery
- **前端**：Vite + React + TypeScript
- **数据库**：PostgreSQL
- **缓存与队列**：Redis

### 3.2 关键数据流
1) `POST /api/analyze` 创建任务
2) Celery Worker 异步执行
3) `GET /api/analyze/stream/{task_id}` SSE 推送进度
4) `GET /api/report/{task_id}` 拉取报告
5) `GET /api/tasks/{task_id}/sources` 获取质量账本
6) DecisionUnit 产出与反馈闭环

---

## 4. 用户侧业务流程

### 4.1 黄金链路
- 注册/登录 → 创建任务 → SSE 进度 → 报告 → 导出/反馈

### 4.2 质量解释
- Report tier：`A_full/B_trimmed/C_scouting/X_blocked`
- 原因与动作：`blocked_reason` / `next_action`
- 账本入口：`/api/tasks/{task_id}/sources`

---

## 5. 前端信息架构

### 5.1 核心页面
- `/` 输入页
- `/progress/{task_id}` 进度页（SSE + 轮询降级）
- `/report/{task_id}` 报告页（LLM 报告 + 质量 Banner + 导出）
- `/insights/{task_id}` 洞察卡（旧卡片）
- `/decision-units` DecisionUnit 反馈页

### 5.2 Admin 页面
- `/admin` Admin 入口
- `/admin/communities/pool` 社区池
- `/admin/communities/import` 导入
- `/admin/tasks/ledger` 任务账本
- `/dashboard` 质量指标

### 5.3 前端关键约定
- Token 存储键：`auth_token`
- API BaseURL：`VITE_API_BASE_URL`
- SSE 使用 `fetch-event-source` 支持 header

---

## 6. 数据模型（摘要）

### 6.1 用户与任务
- `users`, `tasks`, `analyses`, `reports`, `insights`, `beta_feedback`

### 6.2 抓取与缓存
- `crawler_runs`, `crawler_run_targets`, `community_cache`, `posts_hot`, `posts_latest_v`

### 6.3 原始内容
- `posts_raw`, `comments`, `authors`, `posts_quarantine`, `posts_archive`

### 6.4 评分与语义
- `post_scores`, `comment_scores`, `post_semantic_labels`, `post_embeddings`
- `content_labels`, `content_entities`, `noise_labels`, `semantic_main_view`

### 6.5 社区池与发现
- `community_pool`, `discovered_communities`, `tier_suggestions`, `tier_audit_log`, `community_import`

### 6.6 事实与审计
- `facts_snapshot`, `facts_run_log`, `data_audit_events`, `system_health`

### 6.7 决策单元
- `insight_cards`（kind=decision_unit）
- `decision_units_v`（对外读口径）
- `decision_unit_feedback_events`
- `evidences`（含 `content_type/content_id`）

> 全量字段以 DB Atlas 为准：`docs/sop/2025-12-14-database-architecture-atlas.md`

---

## 7. 分析引擎与质量门禁

### 7.1 分析流程
1) 选社区（community_pool + topic_profile）
2) 数据采集（缓存优先 + 受控补抓）
3) 清洗与信号提取（pain/competitor/opportunity + 实体）
4) facts_v2 质量门禁
5) LLM 报告生成（insights 主线 + facts_slice）并落库
6) DecisionUnit 产出（平台级复用）

### 7.2 质量门禁与可解释
- 质量等级：`A_full/B_trimmed/C_scouting/X_blocked`
- 账本字段：`sources.report_tier`、`sources.facts_v2_quality.flags`

### 7.3 报告生成口径（LLM 必经）
- **insights**：算法结论结构（痛点/竞品/机会/行动项/实体榜单）。
- **facts_v2**：证据包 + 门禁 + 审计包；提供 `facts_slice` 作为 LLM 证据输入。
- **报告输出**：必须由 LLM 生成；若 `C_scouting/X_blocked`，只输出解释与下一步动作。
- **report 关键字段口径**：
  - `pain_points/opportunities` 必含 `title/text`
  - `action_items` 必含 `title/category`（category 默认 `strategy`）
  - `purchase_drivers` = `insights.top_drivers`
  - `market_health.ps_ratio`：`facts_slice.ps_ratio` 优先，缺失时回退 `sources.ps_ratio`

### 7.4 报告结构标准（唯一）
报告必须按以下顺序输出（LLM 只负责表达，结论必须来自算法）：
1) 顶部信息：标题 + 简述（赛道/时间窗/数据范围；时间窗默认 12 个月，可被 topic_profile 覆盖）
2) 决策卡片（4 组）：需求趋势 / P/S Ratio / 高潜力社群 / 明确机会点
3) 概览（市场健康度）：竞争饱和度 + P/S 解读
4) 核心战场推荐：分社区画像（画像/痛点/策略）
5) 用户痛点（3 个）：用户之声 + 数据印象 + 解读
6) Top 购买驱动力（2–3 条）
7) 商业机会卡（2 张）

### 7.5 insights 完整性要求（不可缺）
- `trend_summary` / `market_saturation` / `battlefield_profiles` / `top_drivers` 必须由算法产出并落库。
- LLM 不允许自行补脑生成以上字段。

---

## 8. 任务系统与调度

### 8.1 任务系统
- 任务异步执行，队列隔离，多级重试
- 任务状态缓存：`/api/status/{task_id}`

### 8.2 队列与调度
- 队列：`analysis_queue`, `crawler_queue`, `monitoring_queue` 等
- Beat 调度：`tick-tiered-crawl`、`generate-daily-metrics`、`emit-daily-tier-suggestion-decision-units`

### 8.3 预算与熔断
- 自动补量预算（task/user）
- outbox 触发熔断，避免重跑风暴

### 8.4 数据抓取逻辑（SOP 对齐）
- **唯一口径**：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`
- **目标**：把 Reddit 数据稳定搬回 DB + 缓存，输出给分析引擎可消费的语义入口。
- **流程（说人话）**：
  1) Planner 读取 `community_cache` 判定 NEEDS/DONE，生成 `crawler_run_targets`
  2) 写入 `task_outbox`，dispatcher 派发到 `crawler_queue`
  3) Worker 抓取 Reddit → 写 `posts_raw/comments`，更新游标与断点
  4) 更新 `community_cache`（样本/覆盖/回填状态），产出 `DONE_12M` 或 `DONE_CAPPED`
  5) 清洗打分进入 `post_scores_latest_v/comment_scores_latest_v` 供分析引擎读取
- **可追溯表**：`crawler_runs`, `crawler_run_targets`, `task_outbox`, `community_cache`, `posts_raw`, `comments`
- **配置入口**：`backend/config/crawler.yml`、`backend/config/deduplication.yaml`、`backend/config/community_blacklist.yaml`、`backend/config/probe_hot_sources.yaml`  
  （完整配置清单见 SOP 0.2）

### 8.5 数据清洗与价值打分（SOP 对齐）
- **唯一口径**：`docs/sop/数据清洗打分规则v1.2规范.md`
- **目标**：把原始数据从“囤货”变成“鉴宝”，产出 `value_score(0-10)` 与 `business_pool`，并标记噪音/重复。
- **四层流程**：Hygiene（卫生）→ Tagging（分类）→ Scoring（评分）→ Pooling（分池）。
- **落点（说人话）**：
  1) 入库触发器先粗分：写 `posts_raw.value_score/business_pool/spam_category` + `score_version`
  2) 规则评分任务写 `post_scores/comment_scores`（`rule_version='rulebook_v1'`，`is_latest=true` 唯一）
  3) 重复标记：`posts_raw.is_duplicate/duplicate_of_id`（不阻塞入库）
- **边界**：清洗/打分只负责“数据品质与分池”，报告门禁由 facts_v2 负责（见 7.2）。

### 8.6 语义库与报告闭环（Spec 对齐）
- **唯一口径**：Spec 011 + Spec 016（见 0. 对齐口径）
- **现状资产（已落地）**：
  - 语义库与版本：`backend/config/semantic_sets/*`（含 `crossborder_v2.*` 与 `unified_lexicon.yml`）
  - 实体词典：`backend/config/entity_dictionary/*`（含 `crossborder_v2.csv`）
  - 语义抽取脚本：`backend/scripts/extract_lexicon_from_corpus.py`、`backend/scripts/semantic_lexicon_build.py`
- **闭环现状（已落地 + 未自动化）**：
  - 已落地：候选词/语义规则产出、候选审核入口、社区池动态分级、报告生成与质量账本
  - 未自动化：语义激活/淘汰仍以脚本/人工为主（见抓取 SOP 6.4.3）

---

## 9. Admin 运维闭环

### 9.1 社区池管理
- 列表/批量更新/禁用/调级/回滚

### 9.2 导入与审计
- Excel 模板下载 → 上传导入 → 导入历史

### 9.3 任务复盘与指标
- 任务账本（sources + facts）
- 合同健康度与路由指标（contract_health）

### 9.4 合同健康度指标与告警阈值（运营必看）
- **指标聚合**：`contract_health`（按窗口聚合）
  - tier 分布、blocked reason、remediation 数量/去重率、auto_rerun 升级率
  - comments_not_used 触发率、失败类别、端到端耗时（p50/p95）
- **告警阈值**（默认）：
  - `comments_not_used_rate_warn=0.10`
  - `x_blocked_rate_warn=0.15`
  - `data_validation_error_count_warn=1`
- **告警码**：`comments_not_used_rate_high` / `x_blocked_rate_high` / `sources_ledger_validation_failed`

### 9.5 语义候选审核
- semantic_candidates 列表/统计/审批

### 9.6 演练矩阵与故障注入（上线门禁）
- **演练矩阵脚本**：`scripts/phase106_rehearsal_matrix.py`
  - 场景来源：`scripts/phase106_rehearsal_matrix.sample.json`
  - 典型场景：富样本应为 A/B、窄题可降级、topic mismatch 必拦截（X_blocked）
- **故障注入**：`backend/tests/e2e/test_fault_injection.py`
  - 覆盖：Redis 不可用、DB 慢、worker 崩溃重试、Reddit rate limit 失败升级

---

## 10. API 合同（全量摘要）

### 10.1 返回格式
- 直返型：多数业务接口
- 包裹型：多数 Admin 接口 `{ code, data, trace_id }`

### 10.2 模块统计
- auth(3), analysis(1), stream(1), tasks(4), reports(7), insights(2), decision-units(3), beta(1), guidance(1), metrics(2), diagnostics(1), health(1), admin(30), root(1) = 59

### 10.3 admin 关键接口（节选）
- `/api/admin/communities/*`
- `/api/admin/tasks/*`
- `/api/admin/metrics/*`
- `/api/admin/semantic-candidates/*`

**完整接口清单与说明：见本仓库 `docs/API-REFERENCE.md`**（为本 PRD 同步源）。

---

## 11. 导出与反馈
- 报告导出：PDF/Markdown/JSON/CSV
- Beta 反馈：`POST /api/beta/feedback`
- DecisionUnit 反馈：`POST /api/decision-units/{id}/feedback`

---

## 12. 追溯矩阵（模块 → 代码 → 测试 → 记录）

| 模块 | 关键代码 | 测试路径 | 追溯记录 |
|---|---|---|---|
| 数据模型 | `backend/app/models` | `backend/tests/models` | phase106/107 |
| API 合同 | `backend/app/api` | `backend/tests/api` | phase108/109/110 |
| 分析引擎 | `backend/app/services/analysis_engine.py` | `backend/tests/services` | phase106 |
| 任务系统 | `backend/app/tasks` | `backend/tests/tasks` | phase106 |
| 前端交互 | `frontend/src/pages` | `frontend/tests` | phase108/109/110 |
| Admin | `backend/app/api/admin` / `frontend/src/pages/admin` | `backend/tests/api` | phase106/107 |
| DecisionUnit | `backend/app/api/v1/endpoints/decision_units.py` | `backend/tests/api` | phase107 |
| Excel 导入 | `backend/app/services/community_import_service.py` | `backend/tests/api/test_admin_community_import.py` | phase106 |
| 合同健康度 | `backend/app/services/ops/contract_health.py` | `backend/tests/services/ops/test_contract_health.py` | phase106 |
| 监控任务 | `backend/app/tasks/monitoring_task.py` | `backend/tests/tasks/test_celery_beat_schedule.py` | phase106 |
| 演练矩阵 | `scripts/phase106_rehearsal_matrix.py` | `backend/tests/e2e/test_fault_injection.py` | phase106 |
| 语义库资产 | `backend/config/semantic_sets` / `backend/config/entity_dictionary` | `backend/tests/services` | phase-semantic-unification |

---

## 13. 变更控制
- 任何新增/变更必须：更新 PRD-SYSTEM → 更新模块 PRD → 再改实现
- 执行记录必须写入 `reports/phase-log/phase{N}.md`

---

## 14. 数据库快照附录（可追溯口径）

| 资产 | 路径 | 快照日期 | sha256 | 备注 |
|---|---|---|---|---|
| DB Atlas（canonical） | `docs/sop/2025-12-14-database-architecture-atlas.md` | 2026-01-19 | `ece5eeded79440225f048a8db6889eb5d5cb4ea6ccb8499e3ab2dfd58bd53cc4` | 唯一真相 |
| current_schema | `current_schema.sql` | 2026-01-19 | `a03e139af58aecbaeeb6ca39694b2ebe1e78ec14fcdd3a44eb54a74f992f2608` | 实际库快照 |
| DB Atlas（legacy） | `docs/archive/2025-12-14-database-architecture-atlas.md` | 2026-01-19 | `bd89089881c974c892d0faa10e43e348f5e510e47cdc928e75208ec0843b9444` | 历史副本，禁用 |

## 15. SOP/Spec 快照附录（可追溯口径）

| 资产 | 路径 | 快照日期 | sha256 | 备注 |
|---|---|---|---|---|
| 抓取 SOP v3.2 | `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md` | 2026-01-19 | `7066ab677cff0881693202d1af2a3b182c7e7476e4a041697e12905ca29f776c` | 抓取唯一口径 |
| 清洗打分规则 v1.2.1 | `docs/sop/数据清洗打分规则v1.2规范.md` | 2026-01-19 | `3020056a4efbd4db93a8172e23a702ba29080afbcdf874864fe77a164f33cf32` | 清洗/评分口径 |
| 语义库 Spec 011 | `.specify/specs/011-semantic-lexicon-development-plan.md` | 2026-01-19 | `1fe940ed492c500204cc2ca6376ebef4eecd06512b7b33baadb2471904207f67` | 语义库方法论 |
| 语义闭环 Spec 016（spec） | `.specify/specs/016-unified-semantic-report-loop/spec.md` | 2026-01-19 | `ce2b0701414759513962857c704e8d825693d49fa929cf54bb8a65a80bafdcbf` | 闭环规范 |
| 语义闭环 Spec 016（design） | `.specify/specs/016-unified-semantic-report-loop/design.md` | 2026-01-19 | `8bbc85ee4b3bce4886bf3e4adc5b4aaffc31061b5e62e479b63efc0278e088aa` | 实现设计 |
| 语义库指南 | `docs/semantic-library-guide.md` | 2026-01-19 | `086898d3e3a22863a95aa32c27a7ef600a20c413a59168e9955f40f7af23de63` | 辅助口径 |
| 演练矩阵脚本 | `scripts/phase106_rehearsal_matrix.py` | 2026-01-19 | `9d3e4a23a546b73f200c04dedf192935cc14ddcb70c2968988729ce005d9c488` | 生产演练 |
| 演练矩阵样例 | `scripts/phase106_rehearsal_matrix.sample.json` | 2026-01-19 | `6da146a95607f69b63854a80995780a11fdba07e43032526a171447a2923936d` | 场景配置 |
| 故障注入测试 | `backend/tests/e2e/test_fault_injection.py` | 2026-01-19 | `89bc7e1d7cd332b11800ee0f9d1a70f468af4b446909954cb8d24b636d73a315` | 线上故障门禁 |
| 故障注入工具 | `backend/tests/utils/fault_injection.py` | 2026-01-19 | `542af19e1c8f0a82bceb2be7008bfe5b1c7aa8048dbf1c8a9d0c24e0dcbcba12` | 故障管理器 |
| 合同健康度实现 | `backend/app/services/ops/contract_health.py` | 2026-01-19 | `5f54865eb0cfef9bfa0db477e6d78fb611dab048ff6f439a0568a0163b5811c3` | 指标口径 |
| Phase106 记录 | `reports/phase-log/phase106.md` | 2026-01-19 | `00a59afbf0745a5ff7ccd0ff70336370a0d03e7e5396533a86d9380797a4fa24` | 演练与指标证据 |
