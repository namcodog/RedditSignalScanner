# Phase 479 - Analysis Remediation Support 抽离与 3000 线突破

## 时间
- 2026-03-25

## 背景
- 用户要求同时盯住两个硬目标：
  - `backend/app/services/analysis/analysis_engine.py` 压到 `3000` 行以内
  - 主链重构一旦落到可封板状态，就立刻转入“修复结果验证”，不能只看代码变小
- 上一轮结束时，`analysis_engine.py` 仍有 `3387` 行，离 `3000` 还差 `387` 行。

## 本轮动作

### 1. 新增 remediation support 模块
- 新增：
  - `backend/app/services/analysis/analysis_remediation_support.py`
- 抽离：
  - `resolve_topic_profile_backfill_window(...)`
  - `get_remediation_budget_redis(...)`
  - `schedule_auto_backfill_for_insufficient_samples(...)`
  - `schedule_auto_backfill_for_missing_comments(...)`

### 2. 主链改接薄封装 wrapper
- 更新：
  - `backend/app/services/analysis/analysis_engine.py`
- 做法：
  - 保留旧函数名 `_resolve_topic_profile_backfill_window / _get_remediation_budget_redis / _schedule_auto_backfill_for_insufficient_samples / _schedule_auto_backfill_for_missing_comments`
  - 但函数体改成薄封装，只负责转调 remediation support
- 价值：
  - 不破坏现有 monkeypatch 测试接缝
  - 同时把大块 backfill/remediation 逻辑真正搬出主链

### 3. 顺手修掉两类旧合同脏点
- 修复 `_score_community` 漏接缝：
  - `analysis_collection_support.py` 里已有实现，但主链没导回
  - 补回 `score_community as _score_community`
- 修复 `duplicates_summary` 装配合同：
  - 前端 / schema 真实合同是 `list[dict]`
  - `analysis_artifacts.py` 之前错把它当 `dict`
  - 现在改成优先输出列表，同时兼容旧字典输入
- 修复开放题主链的 `min_posts` 旧作用域炸点：
  - 之前只在 `topic_profile` 分支赋值
  - 但后续 quality gate 无论有无 profile 都会读取
  - 现在把默认值提到分支外

## 验证

### 1. 行数验证
- 运行：
  - `cd backend && wc -l app/services/analysis/analysis_engine.py`
- 结果：
  - `analysis_engine.py = 2680`

### 2. remediation / backfill 定向回归
- 运行：
  - `cd backend && pytest tests/services/analysis/test_analysis_engine_comment_backfill.py tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py tests/services/analysis/test_analysis_engine.py tests/services/analysis/test_analysis_artifacts.py -q -k 'resolve_topic_profile_backfill_window or insufficient or backfill or build_sources_payload'`
  - `cd backend && python -m py_compile app/services/analysis/analysis_remediation_support.py app/services/analysis/analysis_engine.py app/services/analysis/analysis_artifacts.py tests/services/analysis/test_analysis_artifacts.py`
- 结果：
  - `8 passed`

### 3. analysis 主链联合回归
- 运行：
  - `cd backend && pytest tests/services/analysis/test_analysis_signal_support.py tests/services/analysis/test_analysis_query_support.py tests/services/analysis/test_analysis_evidence_package_support.py tests/services/analysis/test_analysis_finalization_support.py tests/services/analysis/test_analysis_engine_search_grouping.py tests/services/analysis/test_analysis_engine_collection_mapping.py tests/services/analysis/test_analysis_readiness_support.py tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py tests/services/analysis/test_analysis_rendering.py tests/services/analysis/test_analysis_engine_comment_backfill.py tests/services/analysis/test_analysis_engine_topic_insufficient_samples.py tests/services/analysis/test_analysis_engine.py -q`
- 结果：
  - `85 passed`

### 4. 隔离 live runtime 验证
- 先起隔离 runtime：
  - `python backend/scripts/acceptance/manage_live_runtime.py start --json-only`
- 再跑两条真实链：
  - 标准样板：
    - `python backend/scripts/acceptance/run_live_report_acceptance.py --base-url http://127.0.0.1:8016 --frontend-base-url http://127.0.0.1:3006 --topic-profile-id cross_border_payment_v1 --product-description "帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。" --required-tier A_full`
    - 结果：
      - `task_id = 873697d6-de28-4de3-82f5-398699e29e59`
      - 首轮 `A_full`
  - 开放提问主链：
    - `python backend/scripts/acceptance/run_live_report_acceptance.py --base-url http://127.0.0.1:8016 --frontend-base-url http://127.0.0.1:3006 --product-description "帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。" --required-tier A_full`
    - 结果：
      - `task_id = 46961932-40d4-4652-a3c7-a026eedba525`
      - 首轮 `A_full`
- 验收完成后清理现场：
  - `python backend/scripts/acceptance/manage_live_runtime.py stop --json-only`

## 结果
- `analysis_engine.py` 行数变化：
  - `3387 -> 2680`
- 当前累计减重曲线：
  - `5877 -> 5741 -> 5660 -> 5497 -> 4624 -> 4458 -> 4297 -> 3718 -> 3387 -> 2680`
- 这轮价值：
  - 主链已经正式跌破 `3000`
  - remediation/backfill 这段最脏的历史逻辑不再留在 orchestrator 里
  - analysis 主链第一轮大回归 `85 passed`
  - 标准样板和开放提问两条真实 live 链都首轮 `A_full`

## 下一步
- 继续做第二轮结果验证，不再只盯行数：
  - 横向抽不同题材跑 live
  - 看报告质量是否真的稳定回到 `Full A` 目标口径
- 同时继续盘 `analysis_engine.py` 剩余职责，向中期 `1500` 目标推进
