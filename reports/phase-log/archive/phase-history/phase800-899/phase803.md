# phase803

## 主题

把 `L0 intake freshness` 正式接成 RedditSignalScanner 项目侧的日常发布前置检查。

## 本轮改动

- 新增项目侧 freshness gate service：
  - `backend/app/services/hotpost/intake_freshness_gate.py`
- 新增项目侧一键前置脚本：
  - `backend/scripts/hotpost/run_intake_freshness_gate.py`
- 新增测试：
  - `backend/tests/services/hotpost/test_intake_freshness_gate.py`
  - `backend/tests/scripts/hotpost/test_run_intake_freshness_gate.py`
- 更新 SOP：
  - `docs/sop/2026-04-09-稳态运营成功SOP.md`
  - `docs/sop/2026-04-08-评审与发布SOP.md`

## 固定规则

- 发布前固定顺序：
  1. `sync_topic_metadata.py --json`
  2. `run_offline_publish_plan.py --limit 15`
  3. `freshness gate`
- freshness 口径与 key-os 保持一致：
  - `hot`: `24h / 48h`
  - `signal`: `72h / 120h`
  - `breakdown`: `7d / 10d`
  - `stale_ratio <= 20%`
- 若 gate=`rewrite/fail`：
  - 先 `daily_collect.py`
  - 再 `sync_topic_metadata.py --json`
  - 再 `run_offline_publish_plan.py --limit 15`
  - 再评估 freshness
- 只有常规采集后仍存在热点新鲜度缺口时，才允许继续加跑 `collect_named_topics.py`

## 今日实跑结果

- 命令：
  - `.venv/bin/python backend/scripts/hotpost/run_intake_freshness_gate.py --limit 15 --output-plan backend/tmp/offline-publish-plan-15.json --summary-json backend/tmp/intake-freshness-15.json`
- 初判：
  - `decision = rewrite`
  - `rewrite_reasons = [hot_over_age_limit, signal_target_window_underfilled]`
- 已按合同自动执行：
  - `daily_collect`
  - `sync_topic_metadata`
  - `run_offline_publish_plan(limit=15)`
- 复判结果：
  - `decision = rewrite`
  - `rewrite_reasons = [hot_over_age_limit]`
- 当前不是结构失守：
  - 初判结构：`lane 9/4/2`、`scope 5/5/5`
  - 时间层不过线的主因仍是：
    - `1` 张 `hot` 约 `93h`，超出 `48h` 上限

## 验证

- `python -m py_compile backend/app/services/hotpost/intake_freshness_gate.py backend/scripts/hotpost/run_intake_freshness_gate.py`
- `.venv/bin/pytest backend/tests/services/hotpost/test_intake_freshness_gate.py backend/tests/scripts/hotpost/test_run_intake_freshness_gate.py backend/tests/services/hotpost/test_offline_publish_plan.py backend/tests/services/hotpost/test_workflow_dry_run.py -q --tb=short`
  - `11 passed`

## 结论

- 项目侧现在已经把“先过 freshness gate 再发”接成正式动作。
- `15-baseline` 不再允许默认直接发。
- 今天如果再跑一次 `limit=15`，当前 gate 结果是：
  - `rewrite`
  - 原因：`hot_over_age_limit`
