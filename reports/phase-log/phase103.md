# Phase 103 - 合同封口（RLS 不炸 + facts_v2 分级产出 + 窄题扩样本）

日期：2025-12-29

## 目标（收口“合同”）
把黄金主链路 `/api/analyze -> worker -> /api/report/{task_id}` 的三条硬指标封死：

- 合同A（系统层）：任何合法请求 **绝不因为 RLS/GUC 没设而 500**（跨用户访问 403/404 都行，但不许 500）。
- 合同B（数据层）：料不够时 **可解释 + 自动补量动作**（不是“看起来跑了但没推进/没数据/拿不到报告”）。
- 合同C（真实层）：`sources` 必须能讲清楚 **数据从哪来、抓了多少、为什么是这个 tier、缺口是什么、系统做了什么补救**（尤其 posts/comments 的 DB vs analyzed）。

## 本次核心改动（按 1/2/3/4 任务落地）

### 任务1：facts_quality_check 输出 report_tier（A/B/C/X）
- 已落地：`backend/app/services/facts_v2/quality.py`
  - 质量闸门产出 `tier`：`A_full` / `B_trimmed` / `C_scouting` / `X_blocked`
  - `topic_mismatch` / `range_mismatch` 直接判 `X_blocked`（宁可不出报告，也不跑偏）

### 任务2：threshold 从全局改为 topic 级别
- 已落地：`backend/app/services/topic_profiles.py` + `backend/app/services/facts_v2/quality.py`
  - `TopicProfile` 支持 `pain_min_mentions/pain_min_unique_authors/brand_min_mentions/brand_min_unique_authors/min_solutions`
  - `quality_check_facts_v2()` 自动读取 profile 覆盖默认阈值
- 配置已就位：`backend/config/topic_profiles.yaml`（Shopify Ads 窄题阈值放宽）

### 任务3：Shopify 窄题扩样本策略（扩窗 + 双钥匙入场）
- 已落地：`backend/app/services/analysis_engine.py`
  - `preferred_days` 真正接入样本门槛（sample_guard）：窄题可用更长窗口凑够“能分析”的材料密度
  - Reddit 搜索（用于发现/补充）按 `preferred_days` 自动放宽 `time_filter`（month/year/all）
  - 补抓入库 `_supplement_samples`：
    - 只返回“真正写进 posts_raw 的补量帖子”（避免样本数虚胖）
    - 写 posts_raw 前先 upsert `authors`（修复 `fk_posts_raw_author` 外键失败）
- 配置已就位：`backend/config/topic_profiles.yaml`
  - `mode: operations`（避免 B2B 社区被 market_insight 误杀）
  - `require_context_for_fetch: true` + `context_keywords_any`（“双钥匙”：只提 Shopify 的泛聊不进样本）
  - `preferred_days: 730`（Shopify Ads 这类窄题默认扩窗到 ~24 个月）

### 任务4：报告生成层支持 A/B/C/X
- 已落地：`backend/app/services/analysis_engine.py` + `backend/app/services/report_service.py`
  - `run_analysis` 写入 `sources.report_tier` / `sources.facts_v2_quality`
  - `B_trimmed`：只保留最稳的少量痛点/机会/动作（不硬凑）
  - `C_scouting`：输出“勘探简报”（只给方向感 + 下一步补量建议）
  - `X_blocked`：直接拦截报告（避免误导）
  - ReportService 对 `C_scouting/X_blocked` **强制跳过** LLM/归一化分支（不允许绕过闸门硬生成）

## 额外封口（合同A/B/C 的地基）
- RLS 防 500（missing_ok + 应用层自动注入）：
  - 迁移：`backend/alembic/versions/20251229_000001_make_rls_current_user_id_missing_ok.py`
  - 会话自动注入：`backend/app/db/session.py`（事务级 `set_config('app.current_user_id', ..., true)`）
  - JWT 注入：`backend/app/core/security.py`
  - Celery/任务链路透传 user_id：`backend/app/api/v1/endpoints/analyze.py`、`backend/app/tasks/analysis_task.py`
- 评论纳入口径（修复“comments 永远 0”假闭环）：
  - `backend/app/services/analysis_engine.py` 生成 facts_v2 时会从 DB 拉 `sample_comments_db`，并把 comments 计入 `source_range` / `aggregates.communities`
- 自动补量（样本不足时不再只返回“缺料”，而是下单）：
  - `backend/app/services/analysis_engine.py`：insufficient_samples → 自动下单 `backfill_posts_queue_v2` 并写 `sources.remediation_actions`
- 脚本侧 bug 修复（不影响 API 主链路，但修复单测）
  - `backend/scripts/generate_t1_market_report.py`：`market_landscape` 需要保留平台/渠道全景，不能复用被过滤后的 `brand_co`（否则 platforms/channels 为空）

## 测试与证据
- 重点回归（RLS + 主链路 + 分级输出 + 评论纳入）：
  - `pytest backend/tests/models/test_rls_current_user_context.py backend/tests/services/test_analysis_engine.py backend/tests/api/test_golden_business_flow.py backend/tests/api/test_reports.py -q`
  - 结果：`40 passed, 1 skipped`
- facts_v2/TopicProfile/脚本逻辑回归：
  - `pytest backend/tests/services/test_topic_profiles.py backend/tests/services/test_facts_v2_quality_gate.py backend/tests/services/test_facts_v2_midstream.py backend/tests/services/test_report_logic.py -q`
  - 结果：`29 passed`

## 结论（现在系统能做到什么）
- 不跑偏：topic_profile（尤其 Shopify Ads）会把社区/内容范围锁死，闸门不通过就不出“假报告”。
- 可交付：即便材料偏少，也能稳定产出 `C_scouting` 勘探简报；材料足够才升级到 `B/A`。
- 可追溯：`sources` 里能看到 tier、缺口、补救动作（remediation_actions），不再“看起来跑了其实没推进”。

## 待办（下一步）
- comments 补量自动化：当前 auto backfill 先做 posts，评论回填链路要接入同样的“缺口检测→下单→重试”闭环。
- InsightCard 的 time_window_days 目前固定 30，可考虑改为使用 `sources.lookback_days`（保持口径一致）。

