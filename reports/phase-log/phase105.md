# Phase 105 - 工程化封口 100% 落地清单（A/B/C 全套护栏）

日期：2025-12-29

## 背景（一句话）
Phase103/104 已经把“别跑偏 + 不炸 500 + 评论不再永远 0 + 自动下单补量”打通；Phase105 要把你那段工程化方案 **100% 制度化**：系统自己会预检、会自愈、会报警、会写账本。

## 封口合同（不可谈判）
- 合同A（系统层）：任何合法请求 **绝不因为 RLS/GUC 没设而 500**（跨用户访问 403/404 都行，但不许 500）。
- 合同B（数据层）：料不够时 **必须可解释 + 自动补量动作**（不允许沉默卡住/假跑）。
- 合同C（真实层）：`sources` 必须能回答 **数据从哪来、抓了多少、为什么是这个 tier、缺口是什么、系统做了什么补救**。
- P0.5（隐含条款）：评论必须纳入口径/样本/事实包；**DB 里有评论但 analyzed=0 必须显式标红**，不能默默写 0。

---

## 任务清单（按顺序 1/2/3… 依次落地，不穿插）

### 1) 写“任务清单”当真相源（本文件）
- [x] 已创建 Phase105 checklist
- 验收：清单要包含每个任务的“做法 + 验收标准 + 失败长什么样”

### 2) 合同A：启动自检（rss_app）+ CI 冒烟（rss_app）
- [x] 启动自检：服务启动时，用 rss_app 做一次“RLS 上下文注入 + 读 RLS 表”的 sanity check，失败就不让服务起来
- [x] CI 冒烟：userA 创建 task → userA 拉报告；userB 拉 userA 报告 → 403/404；全程不许出现 `unrecognized configuration parameter app.current_user_id`，更不许 500
- 验收：只要没通过，自检/CI 必须红灯，不能“勉强跑起来”

### 3) 合同B：DataReadinessPreflight（分析前置预检阶段）
- [x] 新增 preflight 阶段：开跑前先算社区集合 + 查 `community_cache` 水位（posts/comments/coverage/backfill_status）
- [x] 不达标时：task 状态明确标记 `blocked=warmup/insufficient_samples`（原因码固定枚举）
- [x] 写入两处：
  - `TaskStatusCache`（API/SSE 直接能看到）
  - `analyses.sources`（即便 blocked 也要落账本）
- 验收：用户不再看到“没动静”，而是“系统在等什么、缺多少、已经下了什么补救单”

### 4) 合同B：补量后自动重跑（自动升级）
- [x] preflight 下单补量后：系统自动重试分析（有限次数 + 指数退避或固定间隔）
- [x] 目标：从 `C_scouting` 自动升级到 `B_trimmed/A_full`（若长期升级不了，也要给出明确失败原因）
- 验收：不用人工点“再跑一次”，系统自己把闭环跑完

### 5) 合同B：卡单看门狗（专杀假死）
- [x] beat 定时扫描 `processing` 超时任务
- [x] 标记 `failure_category=worker_stalled/system_dependency_down`（按口径统一）
- [x] 同步写入审计/health（可被 diag 查到）
- 验收：worker/beat 掉了，不再是“假死”，而是“明确阻塞 + 可追溯”

### 6) 合同C：sources 最小账本 schema 强校验（缺字段不许 completed）
- [x] 定义 sources 的最小必填字段（counts_db/counts_analyzed/blocked/reason/remediation/tier/why/lineage）
- [x] 保存 `completed` 前强校验：缺关键字段 → 直接拒绝写 completed，并把原因写入 task.error_message/审计
- 验收：杜绝“看起来成功但账本空白”

### 7) 合同C：血缘补齐（run/target 可追溯）
- [x] sources/data_lineage 增加 `crawler_run_ids[]` / `target_ids[]`（或等价字段）
- [x] facts_v2 与 sources 要能互相对上（同一批数据，不出现口径精神分裂）
- 验收：任何一份报告都能追到“数据来自哪次 run、哪些 target”

### 8) P1：评论真正参与信号提取（不是只计数/取样）
- [x] 让评论进入 pain/brand/solutions 的证据链（至少 smart_shallow 的高价值评论进入 evidence）
- [x] 质量门禁补充 `comments_not_used/comments_low`（必要时作为降级依据）
- 验收：不再出现“评论补了，但结论还是只看帖子”的半吊子状态

### 9) 最终验收（一次过）
- [x] 合同A：不 500（rss_app 真账号）
- [x] 合同B：缺料必 blocked + 自动下单 + 自动重跑升级（或给出可解释失败）
- [x] 合同C：sources 一眼复盘（DB vs analyzed / tier 原因 / 缺口 / 补救 / lineage）
- [x] 写入 phase-log（执行记录、命令、结果、截图/日志关键片段）

---

## 当前状态（简表）
- 已完成：Phase105-1（清单已创建）
- 已完成：Phase105-2（RLS 启动自检 + rss_app 冒烟测试）
- 已完成：Phase105-3（数据就绪预检 + 状态可见）
- 已完成：Phase105-4（补量后自动重跑）
- 已完成：Phase105-5（卡单看门狗）
- 已完成：Phase105-6（sources 账本强校验）
- 已完成：Phase105-7（血缘补齐：run/target 可追溯）
- 已完成：Phase105-8（评论进入信号证据链 + 门禁补齐）
- 已完成：Phase105-9（最终验收一次过）

### 本阶段证据（Phase105-2）
- 代码落点：
  - `backend/app/db/rls_sanity.py`（启动自检核心逻辑）
  - `backend/app/main.py`（startup hook 接入）
  - `backend/tests/core/test_rls_startup_sanity_check.py`（rss_app 自检测试）
  - `backend/tests/models/test_rls_current_user_context.py`（RLS missing_ok + 注入验证）
  - `backend/tests/e2e/test_multi_tenant_isolation.py`（跨用户 403/不 500）
- 测试命令（通过）：
  - `pytest backend/tests/core/test_rls_startup_sanity_check.py backend/tests/models/test_rls_current_user_context.py backend/tests/e2e/test_multi_tenant_isolation.py -q`

### 本阶段证据（Phase105-3）
- 代码落点：
  - `backend/app/services/analysis_engine.py`（新增 `data_readiness` 预检快照，写入 sources）
  - `backend/app/tasks/analysis_task.py`（blocked/warmup 写入 TaskStatusCache）
  - `backend/app/services/task_status_cache.py`（状态缓存补充 stage/blocked_reason/next_action/details）
  - `backend/app/api/v1/endpoints/tasks.py`（/api/status 透传扩展字段）
  - `backend/app/api/legacy/stream.py`（SSE 透传扩展字段）
- 测试命令（通过）：
  - `pytest backend/tests/services/test_analysis_engine.py::test_run_analysis_insufficient_samples_triggers_auto_backfill_targets backend/tests/test_task_system.py backend/tests/api/test_stream.py backend/tests/api/test_status.py -q`

### 本阶段证据（Phase105-4）
- 代码落点：
  - `backend/app/tasks/analysis_task.py`（warmup auto rerun：排队 + 执行 + 退避 + 次数上限）
- 测试命令（通过）：
  - `pytest backend/tests/test_task_system.py::test_task_warmup_auto_rerun_schedules_followup -q`

### 本阶段证据（Phase105-5）
- 代码落点：
  - `backend/app/tasks/monitoring_task.py`（watchdog 扫描 processing 超时并标记失败 + 写审计）
  - `backend/app/core/celery_app.py`（beat_schedule 增加 watchdog 定时）
  - `backend/app/api/v1/endpoints/tasks.py`（/api/tasks/diag 透出 watchdog 最近运行信息）
  - `backend/app/schemas/task.py`（TaskDiagResponse 扩展字段）
  - `backend/app/models/task.py`（failure_category 口径补齐）
- 测试命令（通过）：
  - `pytest backend/tests/tasks/test_task_watchdog_stalled_tasks.py backend/tests/tasks/test_celery_beat_schedule.py -q`

### 本阶段证据（Phase105-6）
- 代码落点：
  - `backend/app/tasks/analysis_task.py`（`_validate_sources_ledger_min_schema` + 写入前强校验）
  - `backend/app/services/analysis_engine.py`（insufficient_samples 分支补齐最小账本字段）
  - `backend/tests/e2e/utils.py`（fast_run_analysis stub 补齐最小账本字段）
- 测试命令（通过）：
  - `pytest backend/tests/test_task_system.py backend/tests/e2e/test_multi_tenant_isolation.py -q`

### 本阶段证据（Phase105-7）
- 代码落点：
  - `backend/app/services/analysis_engine.py`（补齐 `data_lineage`：crawler_run_ids/target_ids；补量动作回传 target_ids）
  - `backend/app/tasks/analysis_task.py`（sources 账本强校验：新增 data_lineage 必填）
  - `backend/tests/e2e/utils.py`（e2e stub 补齐 data_lineage，避免被强校验拦掉）
  - `backend/tests/services/test_analysis_engine.py`（回归：insufficient_samples + comments_low 场景都能拿到 data_lineage，且 facts_v2 与 sources 一致）
  - `backend/tests/services/test_analysis_engine_comment_backfill.py`（回归：comment backfill action 回传 target_ids 且能在 DB 查到）
  - `backend/tests/test_task_system.py`（sources 账本强校验：缺 data_lineage 必须报错）
- 测试命令（通过）：
  - `pytest backend/tests/services/test_analysis_engine.py::test_run_analysis_insufficient_samples_triggers_auto_backfill_targets backend/tests/services/test_analysis_engine.py::test_run_analysis_applies_facts_v2_quality_gate_with_topic_profile backend/tests/services/test_analysis_engine_comment_backfill.py backend/tests/test_task_system.py::test_sources_ledger_validation_requires_data_lineage backend/tests/e2e/test_multi_tenant_isolation.py -q`

### 本阶段证据（Phase105-8）
- 代码落点：
  - `backend/app/services/analysis_engine.py`（评论参与事实包信号：comment evidence 优先；unique_authors 统计覆盖 comment author；facts_v2.data_lineage 写入 counts_db/comments_pipeline_status）
  - `backend/app/services/facts_v2/quality.py`（新增 `comments_not_used` flag；按需降级到 C_scouting）
  - `backend/tests/services/test_analysis_engine_comment_evidence_chain.py`（回归：帖子中性但评论有痛点时，也能产出 high_value_pains，并使用 comment.id 做 evidence_quote_ids）
  - `backend/tests/services/test_facts_v2_quality_gate.py`（回归：DB 有评论但样本没吃到时，必须打 `comments_not_used` 红灯）
- 测试命令（通过）：
  - `pytest backend/tests/services/test_analysis_engine_comment_evidence_chain.py backend/tests/services/test_analysis_engine.py::test_run_analysis_insufficient_samples_triggers_auto_backfill_targets backend/tests/services/test_analysis_engine.py::test_run_analysis_applies_facts_v2_quality_gate_with_topic_profile backend/tests/services/test_analysis_engine_comment_backfill.py backend/tests/services/test_facts_v2_quality_gate.py::test_quality_gate_flags_comments_not_used_when_db_has_comments -q`

### 本阶段证据（Phase105-9）
- 最终验收命令（通过）：
  - `pytest backend/tests/core/test_rls_startup_sanity_check.py backend/tests/models/test_rls_current_user_context.py backend/tests/services/test_analysis_engine.py::test_run_analysis_insufficient_samples_triggers_auto_backfill_targets backend/tests/services/test_analysis_engine.py::test_run_analysis_applies_facts_v2_quality_gate_with_topic_profile backend/tests/services/test_analysis_engine_comment_backfill.py backend/tests/services/test_analysis_engine_comment_evidence_chain.py backend/tests/services/test_facts_v2_quality_gate.py backend/tests/test_task_system.py::test_task_warmup_auto_rerun_schedules_followup backend/tests/test_task_system.py::test_sources_ledger_validation_requires_data_lineage backend/tests/tasks/test_task_watchdog_stalled_tasks.py backend/tests/tasks/test_celery_beat_schedule.py backend/tests/e2e/test_multi_tenant_isolation.py -q`
