# Phase 104 - 评论闭环封口（comments 口径入闸 + 自动补量 + sources 账本更硬）

日期：2025-12-29

## 目标（补齐 Phase103 的缺口）
把“封口合同”里最容易假闭环的一块（评论链路）收掉：

- 合同B（数据层）：当评论为 0 时，系统必须 **自动下单补抓评论**，而不是沉默降级或假装能结论。
- 合同C（真实层）：`sources` 必须能一眼说清 **库里有多少评论 / 这次吃了多少评论 / 为啥是 0 / 系统做了什么补救**。

## 核心改动

### 1) facts_v2 质量闸门新增“评论最低样本”选项
- 文件：`backend/app/services/facts_v2/quality.py`
- 新增 `min_sample_comments`：
  - 当开启且 `source_range.comments` 不达标 → `flags += ["comments_low"]`
  - `comments_low` 会把 tier **强制降到 `C_scouting`**（避免“没评论也写 B/A”）
- 支持 topic_profile 覆盖（见下条）。

### 2) TopicProfile 支持评论阈值（窄题专用）
- 文件：`backend/app/services/topic_profiles.py`
- 新增字段：`min_sample_comments`
- 配置：`backend/config/topic_profiles.yaml` + `config/topic_profiles.yaml`
  - Shopify profile 增加：`min_sample_comments: 1`
  - 语义：Shopify Ads 这类窄题 **至少要吃到 1 条评论证据**，否则只出勘探版并触发补量。

### 3) 评论自动补量下单（outbox + backfill_comments）
- 文件：`backend/app/services/analysis_engine.py`
- 新增 `_schedule_auto_backfill_for_missing_comments()`：
  - 当 `topic_profile` 存在且 `sample_comments_db` 为空 → 自动创建 `backfill_comments` targets
  - 写入：
    - `crawler_runs` / `crawler_run_targets`
    - `task_outbox`（event_type=`execute_target`，queue=`COMMENTS_BACKFILL_QUEUE`）
  - 同时把动作记录到：`sources.remediation_actions`

### 4) sources 账本更硬（DB vs analyzed + 状态码）
- 文件：`backend/app/services/analysis_engine.py`
- 新增字段：
  - `sources.counts_db.posts_current`
  - `sources.counts_db.comments_total/comments_eligible`
  - `sources.counts_analyzed.posts/comments`
  - `sources.comments_pipeline_status`（ok/disabled/all_noise/filtered）
- `C_scouting` 勘探简报里补充：评论数量 + 状态 + “系统已自动补量”的一句话提醒。

## 测试
- 新增/更新：
  - `backend/tests/services/test_facts_v2_quality_gate.py`（评论闸门 + profile 覆盖）
  - `backend/tests/services/test_analysis_engine_comment_backfill.py`（评论补量 targets/outbox）
  - `backend/tests/services/test_analysis_engine.py`（Shopify profile 评论为 0 → C_scouting + 自动补量）
- 已执行并通过：
  - `pytest backend/tests/services/test_facts_v2_quality_gate.py -q`
  - `pytest backend/tests/services/test_analysis_engine_comment_backfill.py -q`
  - `pytest backend/tests/services/test_topic_profiles.py -q`
  - `pytest backend/tests/services/test_analysis_engine.py -q`
  - `pytest backend/tests/models/test_rls_current_user_context.py backend/tests/api/test_golden_business_flow.py backend/tests/api/test_reports.py -q`

## 备注
- Serena MCP 工具本次调用失败（Transport closed），已改用 repo 内置测试与代码检索完成定位与验收。

