# Phase 106 - 稳定态运营封口（不崩 / 不贵 / 不吵 / 可持续）

日期：2025-12-29

## 背景（一句话）
Phase105 已经把“系统不撒谎、能自愈、账本可追溯”封死；Phase106 要把它变成**可长期运营的稳定态**：真实 Reddit 环境抖动/限流/脏数据/突发热点下，系统依然可控、可观测、不会自嗨下单把自己跑崩。

## Phase106 不可破坏的底线（沿用 Phase105 合同）
- 合同A：任何合法请求绝不因为 RLS/GUC 缺失而 500（跨用户访问 403/404 都行，但不许 500）
- 合同B：料不够必须可解释 + 自动补量动作（不允许沉默卡住/假跑）
- 合同C：`sources` 一眼复盘（DB vs analyzed / tier 原因 / 缺口 / 补救 / lineage）
- P0.5：评论纳入口径/样本/事实包；DB 有评论但 analyzed=0 必须显式标红

> Phase106 的所有改动都必须满足：不破坏以上合同；只加“运营保险丝”。

---

## 任务清单（按顺序 1/2/3… 依次落地，不穿插）

### 1) 写“任务清单”当真相源（本文件）
- [x] 已创建 Phase106 checklist
- 验收：每个任务必须写清楚：做法 / 验收标准 / 失败长什么样 / 产出证据（命令+结果）

### 2) 合同字段 → 可运营指标面板 + 报警阈值（不再盲飞）
目标：把 Phase105 的“传感器”（sources/diag/watchdog/status）变成运营仪表盘，能 5 分钟内定位到 run/target/队列/失败类别。
- [x] 新增 `contract_health` 指标聚合（按小时/天）：tier 分布、blocked 分布、remediation 数量/去重率、auto_rerun 升级成功率、comments_not_used 触发率、counts_db vs counts_analyzed 缺口分布、端到端耗时分解（按 stage）
- [x] 指标写入 Redis dashboard（复用 `dashboard:performance`）并提供只读 API（Admin）
- [x] 报警：阈值触发时能自动打红灯（日志/审计事件），且包含可定位信息（task_id/run_id/queue）
- 验收：
  - 任意指标异常 → 5 分钟内能从 sources/diag 追到具体 run/target/队列
  - 不影响主链路：指标失败不许拖慢分析/抓取

落地说明（做了什么）
- 新增 contract_health 聚合：`backend/app/services/ops/contract_health.py`
  - 输出核心指标：tier 分布、blocked reason、remediation targets + outbox 去重、auto_rerun 升级率、comments_not_used、失败类别、耗时（p50/p95）
- 监控任务（写入 Redis + 报警/审计）：`backend/app/tasks/monitoring_task.py`
  - 新 Celery 任务：`tasks.monitoring.monitor_contract_health`
  - 写入：`dashboard:performance` hash 的 `contract_health` 字段（同一份 payload）
  - 报警：阈值触发会 `_send_alert(...)`，并写入 `data_audit_events`（reason=alert.code）
- Admin 只读接口：`backend/app/api/admin/metrics.py`
  - `GET /api/admin/metrics/contract-health`：返回最新 contract_health（从 `dashboard:performance` 读）
- 路由调用指标补齐状态码：`backend/app/middleware/route_metrics.py`（支持统计 `golden|status|200` 等，便于后续做 500 率拆分）
- remediation “去重牙齿”记账：`backend/app/services/analysis_engine.py`
  - `remediation_actions[]` 里新增 `outbox_enqueued/outbox_deduped`（用于看“自动下单有没有打风暴/有没有重复下单”）

证据（测试）
- 运行：`SKIP_DB_RESET=1 pytest -q backend/tests/api/test_route_metrics.py backend/tests/services/ops/test_contract_health.py backend/tests/services/test_admin_metrics.py backend/tests/tasks/test_celery_beat_schedule.py`
- 结果：26 passed

### 3) 自动补量/自动重跑加“预算牙齿”（防自激振荡）
目标：在“闭环有效”的前提下，避免自动下单风暴/重跑风暴/队列雪崩。
- [x] task 级预算：每个 task 补量 targets 上限（posts+comments 合计），超出必须停止并在 sources 写清“预算耗尽/缺口还剩多少”
- [x] user/tenant 级预算：时间窗预算（每小时/每天 targets 上限），按 membership 可分档
- [x] 全局熔断：当队列积压/429 激增/系统依赖异常时，补量策略自动降级（少下单 + 拉长重试间隔），但必须“诚实可解释”
- [x] 强校验的生产配套：`sources_ledger_validation_failed` 必须变成可运营指标/报警（避免雪崩式失败无感）
- 验收：
  - 故障/限流场景下不会出现 targets 洪峰、warmup 重跑风暴、队列被塞爆导致全站不可用
  - 合同B仍成立：缺料会解释，会补救（在预算内），不会假跑

落地说明（做了什么）
- 补量预算牙齿（task + user/hour + user/day）：
  - 代码：`backend/app/services/analysis_engine.py`
  - key（Redis，best-effort）：`budget:remediation:task:{task_id}`、`budget:remediation:user_hour:{user_id}:{YYYYMMDDHH}`、`budget:remediation:user_day:{user_id}:{YYYYMMDD}`
  - 写入位置：`sources.remediation_actions[].budget_detail`（包含 max/used/remaining + 本次 max_targets_allowed）
- 全局熔断（防下单风暴）：
  - 基于 outbox backlog：`task_outbox(status='pending')` >= `REMEDIATION_OUTBOX_PENDING_FUSE_THRESHOLD` 时，自动把 `max_targets_allowed` 压到 `REMEDIATION_FUSE_MAX_TARGETS`
  - 结果同样写入：`sources.remediation_actions[].budget_detail.circuit_breaker`
- 自动重跑收紧（避免“预算拦住了还在重跑”）：
  - 代码：`backend/app/tasks/analysis_task.py`
  - 规则：`remediation_actions` 必须有 `targets>0` 才允许触发 warmup auto rerun（否则直接不重跑，next_action=manual_intervention）
- posts 回填计划支持上限（避免先建一堆 targets 再截断）：
  - 代码：`backend/app/services/discovery/auto_backfill_service.py`
  - 新增参数：`plan_auto_backfill_posts_targets(..., max_targets=...)`

可配参数（环境变量，默认值见代码）
- `REMEDIATION_BUDGET_ENABLED=1`
- `REMEDIATION_TASK_TARGET_BUDGET=200`
- `REMEDIATION_USER_HOURLY_TARGET_BUDGET_FREE/PRO/ENTERPRISE`
- `REMEDIATION_USER_DAILY_TARGET_BUDGET_FREE/PRO/ENTERPRISE`
- `REMEDIATION_OUTBOX_PENDING_FUSE_THRESHOLD=5000`
- `REMEDIATION_FUSE_MAX_TARGETS=3`

证据（测试）
- 运行：`SKIP_DB_RESET=1 pytest -q backend/tests/tasks/test_warmup_auto_rerun_budget_guard.py backend/tests/services/test_auto_backfill_posts_targets_cap.py`
- 结果：5 passed

### 4) 前端与 Admin 对齐（让人类看得懂、用得对）
目标：用户/运营能看懂“blocked/warmup/scouting”，能自助定位，减少工单。
- [x] 前端状态：展示 stage / blocked_reason / next_action / 预计重试时间（从 `/api/status` / SSE）
- [x] Admin 复盘页（最小形态）：输入 task_id → 输出 sources ledger + facts_v2_quality + lineage(run/target) + comments_not_used 是否触发
- 验收：
  - 任意 C_scouting / X_blocked：前端必须明确“为什么 + 下一步”，不伪装成成功完整版
  - 任意失败：Admin 能一眼定位是 RLS/预算/队列/数据链路缺字段

落地说明（做了什么）
- Progress 等待页把“状态解释”说清楚（Phase105/106）：`frontend/src/pages/ProgressPage.tsx`
  - 展示：stage / 卡点原因 / 下一步 / 预计重试（next_retry_at）
  - warmup/auto_rerun 不再自动跳到 report（避免伪装成“已出完整报告”），改为轮询等待下一步
- Admin 复盘页（前端）：`frontend/src/pages/admin/TaskLedgerPage.tsx`
  - 路由：`/admin/tasks/ledger`
  - 输入 task_id → 展示 task / sources / facts_snapshot（并把 comments_not_used 当红灯）
- Admin 复盘接口（后端）：`backend/app/api/admin/tasks.py`
  - `GET /api/admin/tasks/{task_id}/ledger`（require_admin）
  - 返回：task + analysis.sources + 最新 facts_snapshot（可选 include_package=true 带 v2_package）

证据（测试）
- 前端：`cd frontend && npm run type-check && npm test`
- 后端：`SKIP_DB_RESET=1 pytest -q backend/tests/api/test_admin_task_ledger.py`

### 5) 真人黄金路径“生产演练矩阵”（上线门禁）
目标：不是只跑一次 Shopify，而是可复现的演练矩阵（富样本/窄题/必拦截/故障注入）。
- [x] 演练矩阵脚本化（可复现）：固定 topic_profile + 固定时间窗 + 固定验收输出落点
- [ ] 覆盖 4 类场景（当前 2/4 已通过）：
  - [x] 富样本：稳定出 B/A（验证不会误降级）
  - [ ] 窄题（Shopify Ads）：blocked → 自动补量 → 自动重跑升级；评论证据链在报告里出现
  - [x] 必拦截：topic_mismatch/range_mismatch → X_blocked 且只给拦截说明
  - [ ] 故障注入：worker/beat/redis 任一短暂不可用 → watchdog/diag/状态解释能顶住
- [ ] SLO 候选：端到端耗时（/api/analyze → /api/report 可取）落在 PRD-03 “5 分钟内可用报告”的可控范围内（允许 warmup 场景延后，但必须可解释）
- 验收：矩阵一次过，并把结果写入本 phase-log（含关键日志片段/截图/命令）

落地说明（做了什么）
- 增加可复现脚本：`scripts/phase106_rehearsal_matrix.py`
  - 走黄金链路：`POST /api/analyze` → 轮询 `GET /api/status/{task_id}` → `GET /api/report/{task_id}`
  - 同时拉 Admin 账本：`GET /api/admin/tasks/{task_id}/ledger`，拿 sources/facts_snapshot 用来复盘 tier/flags/补量动作
- Sample 配置：`scripts/phase106_rehearsal_matrix.sample.json`

运行方式（本地/预发）
1) 先起服务：`make dev-golden-path`（确保 worker/redis 都在线）
2) 准备 token：`export PHASE106_TOKEN="..."`（必须是能访问 /api 的真实用户）
3) 如果要跑 admin ledger 校验：确保该用户 email 在 `ADMIN_EMAILS` 里
4) 执行：`python scripts/phase106_rehearsal_matrix.py --config scripts/phase106_rehearsal_matrix.sample.json --out /tmp/phase106_matrix.json`

最新演练结果（2025-12-30）
- 证据文件：
  - `/tmp/phase106_matrix_quick_out.json`（富样本 + 必拦截）
  - `/tmp/phase106_shopify_warmup_evidence.json`（Shopify 窄题 warmup/自愈证据）
- 结果（核心只看 tier + blocked/next_action）：
  - rich_sample_should_be_A_or_B：`A_full`
  - must_block_topic_mismatch：`X_blocked`（topic_mismatch）
  - narrow_shopify_ads_should_not_lie：
    - 当前：`stage=warmup` / `blocked_reason=insufficient_samples` / `report_tier=C_scouting`
    - 系统动作：已自动下单补量（`remediation_actions[].type=backfill_posts`），并安排 `auto_rerun`（attempt/max_attempts 与 next_retry_at 见 status.details）
    - 备注：完整矩阵跑到“最终 done”需要等待下一次 auto_rerun（分钟级），所以本次把 Shopify 单独存证据，避免脚本跑到超时

本轮补齐点（为什么富样本之前过不了）
- 根因：facts_v2 的 high_value_pains 之前是“句子级碎片”，导致每条痛点 mentions=1 / unique_authors<=1，永远过不了 quality gate → 误降级成 C_scouting。
- 修复：`backend/app/services/analysis_engine.py` 新增 `_cluster_pain_signals_for_facts`，把 pain_points 合并成少量“痛点簇”（含一个“汇总簇”），让 mentions/authors 能真实累计。
- 证据（测试）：
  - `PYTEST_RUNNING=1 pytest -q backend/tests/services/test_analysis_engine.py`
  - `PYTEST_RUNNING=1 pytest -q backend/tests/services/test_analysis_engine_pain_aggregation.py`

---

## 当前状态（简表）
- 已完成：Phase106-1 ~ 4（清单 / 指标面板 / 预算牙齿 / 前端+Admin 对齐）
- 进行中：Phase106-5（需要在本地/预发把 4 类场景跑一遍，并把输出贴回本文件）

---

## 2025-12-30 本轮补齐（回归全绿 + Shopify 自愈存证）

统一反馈四问（这次按“收口合同”说人话）：
1) 发现了什么问题/根因？
   - Phase106 增加了 Shopify 窄题的 `min_posts=10` 早退逻辑后，部分单测只喂了 1-2 条帖子，导致直接走 `insufficient_samples`，拿不到 `facts_v2_package`，测试就炸了。
   - 另外有些单测虽然喂了多条，但文本太像，被去重器（MinHash/阈值 0.85）合并成 <10 条，也会触发同一个早退。
2) 是否已精确定位？
   - 是：触发点在 `backend/app/services/analysis_engine.py` 的 topic-level `min_posts` early return（发生在 dedup 之后）。
3) 精确修复方法？
   - 只改测试数据与预期：让 Shopify 相关单测喂够 >=10 条「Shopify + 语境词」帖子，并且每条加足够差异，避免被 dedup 合并。
   - 涉及测试文件：
     - `backend/tests/services/test_analysis_engine.py`
     - `backend/tests/services/test_analysis_engine_comment_evidence_chain.py`
4) 下一步做什么？
   - Phase106-5 继续补齐 4/4 场景：把 Shopify 窄题跑到 “auto_rerun 最终态（done 或 manual_intervention）”，再补一次故障注入（worker/redis 任一短暂不可用）。
5) 这次修复效果是什么？
   - 回归测试已全绿（见命令记录），且 Shopify 场景已稳定进入 `warmup(insufficient_samples) → 自动补量 → auto_rerun_scheduled` 的“诚实自愈”链路（证据见上述 /tmp 文件）。

证据（命令 + 结果）
- 回归：`pytest -q backend/tests/services/test_analysis_engine.py backend/tests/services/test_analysis_engine_comment_evidence_chain.py backend/tests/services/test_analysis_engine_comment_backfill.py backend/tests/services/test_analysis_engine_topic_profile_filters.py backend/tests/services/test_analysis_engine_topic_insufficient_samples.py backend/tests/api/test_task_sources_ledger.py`
- 真人演练（本地黄金路径）：`make dev-golden-path`
- 矩阵（富样本+必拦截）：`python scripts/phase106_rehearsal_matrix.py --config /tmp/phase106_matrix_quick.json --out /tmp/phase106_matrix_quick_out.json`
- Shopify 自愈证据：`/tmp/phase106_shopify_warmup_evidence.json`

---

## 2025-12-30 本轮补齐（把“故障注入”跑成真：worker down 不再被 inline 假象掩盖）

统一反馈四问（这次按 Phase106 的“演练矩阵/故障注入”说人话）：
1) 发现了什么问题/根因？
   - 之前“停掉 worker 也能秒出 completed”的现象，不是系统太强，而是 **`/api/analyze` 根本没把任务发到 Celery**：它一直在 API 进程里 inline 跑完了。
   - 进一步定位发现：本地 `backend/.env` 写死了 `ENABLE_CELERY_DISPATCH=0`，同时 `backend/app/core/config.py` 在开发环境会强制用 `backend/.env` 覆盖 shell 环境变量，导致你就算 `export ENABLE_CELERY_DISPATCH=1` 也没用 → 永远 inline。
   - 另外，`make celery-restart/dev-backend/restart-backend` 这些命令看似有写，但其实每行单独起 shell，`. $(COMMON_SH)` 里的函数下一行就丢了 → 关键演练动作不好自动化。
2) 是否已精确定位？
   - 是：
     - 变量覆盖根因在 `backend/app/core/config.py` 的 dotenv 加载策略 + 本地 `backend/.env` 的默认值。
     - Makefile 失效根因在 `makefiles/celery.mk` / `makefiles/dev.mk` / `makefiles/ops.mk` 的 “source 在上一行、函数在下一行”。
3) 精确修复方法？
   - 让 env 的优先级变得可控（shell/CI > backend/.env > 根目录 .env），避免“我明明 export 了却不生效”：
     - 新增：`backend/app/core/config.py` 的 `_load_dotenv_with_precedence(...)`
     - 新增测试：`backend/tests/core/test_dotenv_precedence.py`
   - 给 `/api/analyze` 加“派发模式可观测”（避免再被 inline 假象糊弄）：
     - `backend/app/api/v1/endpoints/analyze.py`：把 `dispatch_mode` 写进 `TaskStatusCache.details`（并加 0.3s 超时兜底，Redis 挂了也不拖慢创建任务）
   - 修 Makefile 的 worker/服务管理命令，保证可复现演练：
     - `makefiles/celery.mk` / `makefiles/dev.mk` / `makefiles/ops.mk`：所有依赖 common.sh 的函数调用统一改成 `bash -lc '. $(COMMON_SH); ...'`
4) 下一步做什么？
   - 用同一套方式再补一个“Redis 不可用 / broker 不可用”的故障注入（确保是 503/可解释，而不是 500/假死）。
   - 继续补齐 Phase106-5 的四类场景矩阵，把结果都写回本文件当“演练账本”。
5) 这次修复效果是什么？
   - “worker down 故障注入”终于跑成真：停掉 worker 后创建分析任务，Redis `analysis_queue` 会真实 +1，且 `/api/status` 里能看到 `details.dispatch_mode=celery`（证明确实发到了 Celery，而不是 inline 假完成）。
   - 同时 `/api/tasks/stats` 会从 `active_workers=1` 变成 `0`，恢复 worker 后回到 `1`，整个过程 API 不 500。

证据（命令 + 结果）
- 单测：
  - `pytest -q backend/tests/core/test_dotenv_precedence.py`
  - `pytest -q backend/tests/api/test_analyze.py::test_create_analysis_task`
- 故障注入存证（worker down）：
  - 证据文件：`/tmp/phase106_worker_down_injection_evidence.json`
  - 关键结果（摘录）：
    - baseline: `active_workers=1`
    - worker_down: `active_workers=0`
    - analyze: `201` 且 `details.dispatch_mode=celery` + `redis analysis_queue 0 -> 1`
    - restore: `active_workers=1`

---

## 2025-12-30 本轮补齐（故障注入：broker 不可用时不许“卡死/假成功”）

统一反馈四问（这次聚焦 “Redis/broker 不可用” 的线上现实）：
1) 发现了什么问题/根因？
   - 当 broker 不可达时，`celery_app.send_task(...)` 会 **同步阻塞很久**（API 请求直接超时），这违反 Phase106 的“**不吵/不崩**”。
   - 同时 `/api/tasks/stats` 会因为顺序调用 `inspect.active/reserved/scheduled`，每个都等到 timeout，叠加后容易 **整页卡住/超时**，导致监控页也跟着挂。
2) 是否已精确定位？
   - 是：
     - `/api/analyze` 的阻塞点就是 `celery_app.send_task(...)`（同步 I/O + broker 不可达）。
     - `/api/tasks/stats` 的阻塞点是 `inspect.*` 的顺序等待叠加（单次 1s 变成 3s+）。
3) 精确修复方法？
   - `send_task` 改成“**线程里跑 + 超时兜底**”，保证 API 一定能在可控时间内返回 503：
     - `backend/app/api/v1/endpoints/analyze.py`：`asyncio.to_thread + asyncio.wait_for(CELERY_DISPATCH_TIMEOUT_SECONDS)`
   - Celery broker 连接超时收紧（避免线程卡太久，防线程堆积）：
     - `backend/app/core/celery_app.py`：`broker_transport_options.socket_connect_timeout/socket_timeout`
   - `/api/tasks/stats` 改成“**线程里收集 + 小 timeout + 总超时兜底**”，避免 broker 异常时把监控页拖死：
     - `backend/app/api/v1/endpoints/tasks.py`（同样同步收集放进 to_thread，inspect/ping 用 0.2s 小 timeout）
     - `backend/app/api/legacy/tasks.py`（保持一致）
   - 并且继续遵守“不留孤儿 task”：broker down 返回 503 时会删掉刚创建的 task（用户重试不会越堆越多）。
4) 下一步做什么？
   - 把这一套“broker down 快速失败”的证据纳入 Phase106 演练矩阵，形成固定 SOP（预发/生产同样可跑）。
5) 这次修复效果是什么？
   - broker down 时 `/api/analyze` 能稳定返回 503（不假成功、不卡死），且 DB 不会留下 task 垃圾行。
   - broker down 时 `/api/tasks/stats` 不再超时挂死，而是快速返回 `0/0/0/0`（监控页至少能打开、能判断“系统依赖掉了”）。

证据（测试）
- `pytest -q backend/tests/api/test_analyze.py -k \"returns_503_when_celery_broker_down or returns_503_fast_when_send_task_hangs\"`
- `pytest -q backend/tests/api/test_task_stats.py`

证据（真人故障注入存证）
> 说明：本机 Redis 由系统服务托管，`make redis-stop` 会被自动拉起；因此用“broker 指向不存在端口”模拟 broker down（更贴近线上：网络不可达/端口不通）。
- 证据文件：`/tmp/phase106_broker_down_injection_evidence_v3.json`
- 关键结果（摘录）：
  - `/api/tasks/stats`：`200` 且约 `1.5s` 内返回 `active_workers=0`（不挂死）
  - `/api/analyze`：`503` 且约 `2.0s` 内返回 `Analysis queue unavailable...`
  - `tasks_count_before=0` 且 `tasks_count_after=0`（无孤儿 task）

---

## 2026-01-02 本轮补齐（止血：Celery worker 反复刷 pain_tag enum 报错）

统一反馈四问（这次聚焦“日志不吵、worker 不炸”）：
1) 发现了什么问题/根因？
   - Celery worker 日志里反复刷：`LookupError: 'pain_tag' is not among the defined enum values (content_category)`。
   - 根因是 DB 里 `content_labels.category` 存在历史脏值 `pain_tag`；而 `TierIntelligenceService.calculate_community_metrics()` 以前用 ORM 直接 `select(ContentLabel)` 读回，SQLAlchemy 在把字符串转成 Enum 时当场炸掉 → 任务里不断重试/循环调用就会“刷屏”。
2) 是否已精确定位？
   - 是：触发点在 `backend/app/services/tier_intelligence.py` 的 `calculate_community_metrics()`（读取 ContentLabel 阶段）。
3) 精确修复方法？
   - 不再让 ORM Enum 直接碰脏值：改成查询时 `CAST(category AS text)` + `CASE` 映射，把历史 `pain_tag` 当作 `pain` 处理，并用 `ContentLabelDatum` 做轻量承载，避免 Enum 反序列化炸 worker。
   - 顺手把 `labeling_coverage` 的口径纠正为“只算 post 的 label”（避免把 comment label 也算进去导致比例 > 1）。
4) 下一步做什么？
   - 观察一轮 worker 日志，如果还有类似 Enum 脏值（比如 aspect/entity_type），按同样思路在“读入口径”做容错兜底；数据层的历史修复（UPDATE 清脏）可单独安排，不阻塞本次封口。
5) 这次修复效果是什么？
   - `calculate_community_metrics()` 在遇到历史 `pain_tag` 时不再抛异常，worker 日志的刷屏噪音应该直接消失（同类错误不再能被触发）。

证据（测试）
- `pytest -q backend/tests/services/test_tier_intelligence_service.py`
- `pytest -q backend/tests/api/test_admin_tier_intelligence_api.py`

---

## 2026-01-02 本轮补齐（Phase106-5 矩阵跑满 + Shopify 评论口径一致性）

统一反馈四问（大白话）：
1) 发现了什么问题/根因？
   - Shopify 窄题已经能抓到评论，但 facts_v2 有时会被硬拦截成 `X_blocked(range_mismatch)`：不是数据“缺”，而是 **帖子/评论的社区名大小写不一致**（比如 `r/FacebookAds` vs `r/facebookads`），导致 aggregates 里 `comments=0`，source_range 里 `comments>0`，门禁直接判“口径对不上”。
2) 是否已精确定位？
   - 是：触发点在 `backend/app/services/analysis_engine.py` 的 `aggregates.communities[].comments` 映射（key 不一致就会丢评论计数）。
3) 精确修复方法？
   - 统计/样本阶段统一社区名口径为 `r/<lower>`（帖子/评论/样本/聚合全部走同一套归一化），避免“有评论却被当成 0”。
   - 新增回归测试：`backend/tests/services/test_analysis_engine_aggregates_comment_consistency.py`
4) 下一步做什么？
   - Phase106-6：把 Celery 日志里剩余两条 MV refresh 权限噪音清掉（不影响功能，但会“很吵”）。
5) 这次修复效果是什么？达到了什么结果？
   - Shopify 窄题能稳定产出 `C_scouting`，并且 sample_comments/aggregates/comments/source_range 全部对齐，不再因为 range_mismatch 被 `X_blocked`。

证据（演练矩阵 3/3 + 口径校验）：
- 矩阵脚本：`python scripts/phase106_rehearsal_matrix.py --config scripts/phase106_rehearsal_matrix.sample.json --out /tmp/phase106_matrix_run3_20260102_143815.json`
- 输出文件：`/tmp/phase106_matrix_run3_20260102_143815.json`
  - rich_sample_should_be_A_or_B → `A_full`
  - narrow_shopify_ads_should_not_lie → `C_scouting`（comments=23，已下单补量）
  - must_block_topic_mismatch（mismatch_demo_v1）→ `X_blocked`

---

## 2026-01-02 本轮补齐（不吵：MV refresh 权限报错不再刷屏）

统一反馈四问（大白话）：
1) 发现了什么问题/根因？
   - Celery worker 会周期性刷两条错误：`must be owner of materialized view posts_latest/post_comment_stats`。
   - 根因：本地/某些环境里应用 DB 账号不是这两个物化视图的 owner，`REFRESH MATERIALIZED VIEW` 会直接报错；定时任务反复跑就反复刷。
2) 是否已精确定位？
   - 是：触发点在 `backend/app/tasks/maintenance_task.py` 的 `_refresh_view_with_fallback()`（权限错误直接 raise，Celery 认为任务失败）。
3) 精确修复方法？
   - 权限错误不再抛异常：改成“跳过刷新 + 写审计 + 只告警一次”，任务返回 `status=skipped`，避免刷屏/重试风暴。
4) 下一步做什么？
   - 如果线上需要真正刷新：用 owner 角色跑（或 DBA 调整 owner/权限），这里的降级逻辑不影响线上，只是让“没权限的环境”不吵不炸。
5) 这次修复效果是什么？
   - 同样的权限错误不再导致任务失败/刷 stacktrace；worker 只会对每个 view 打一次 warning，后续安静跳过。

证据（本地触发一次任务验证）：
- 触发命令：
  - `python -c 'from app.tasks import maintenance_task; print(maintenance_task.refresh_posts_latest())'`
  - `python -c 'from app.tasks import maintenance_task; print(maintenance_task.refresh_post_comment_stats())'`
- 结果示例：返回 `{'status': 'skipped', 'skipped_reason': 'permission_denied'}`，并且不再出现 “must be owner …” 的报错堆栈刷屏。
