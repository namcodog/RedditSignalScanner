# Phase 243 - Phase240 Round 3（残留非确定性链路终极收口）

## 这轮改了什么

### 1. 确定性模式下彻底跳过残余 LLM
- 文件：`backend/scripts/report/generate_t1_market_report.py`
- 新增 `_deterministic_topic_expansion()`，在显式传入 `--anchor-ts` 时：
  - 不再调用 `_expand_topic_semantically()`
  - 直接用 `_tokenize_topic()` 做简单分词
  - `exclusion_tokens = set()`
  - `vertical = "other"`
- 同时在确定性模式下跳过：
  - `PersonaGenerator.generate_batch()`
  - `_fetch_top_brands_from_llm()`

### 2. `t1_stats.py` 的时间窗全部改为固定 anchor
- 文件：`backend/app/services/analysis/t1_stats.py`
- 新增本地 `_resolve_anchor_ts()`，统一把可选 `anchor_ts` 归一成 UTC。
- 给以下函数加了 `anchor_ts: datetime | None = None`：
  - `build_stats_snapshot()`
  - `build_entity_sentiment_matrix()`
  - `fetch_topic_relevant_communities()`
  - `write_snapshot_to_file()`
  - `_fetch_posts_comments()`
- 原来主链里遗漏的 `NOW()` 时间窗，全部改成调用方传入的固定时间点或 Python 侧先算好的 cutoff。
- 顺手把 `T1StatsService._fetch_sample_title()` 里多余的 `NOW()` 也一起清掉。

### 3. 调用方把 anchor_ts 传通
- 文件：`backend/scripts/report/generate_t1_market_report.py`
- 报告脚本对以下调用都补了 `anchor_ts=anchor_ts`：
  - `fetch_topic_relevant_communities()`
  - `build_stats_snapshot()`
  - `build_entity_sentiment_matrix()`
  - `write_snapshot_to_file()`

### 4. validator 断路径保护
- 文件：`backend/scripts/report/generate_t1_market_report.py`
- `validate_facts_v2.py` 改成先 `exists()` 检查。
- 文件不存在时只打印：
  - `ℹ️ Validator script not found, skipping: ...`
- 不再抛路径错误，也不再污染确定性验证日志。

## 新增/补强测试

### `backend/tests/services/report/test_report_logic.py`
- `test_deterministic_topic_expansion_uses_simple_tokenization`

### `backend/tests/services/analysis/test_t1_stats_determinism.py`
- `test_build_stats_snapshot_uses_fixed_anchor_timestamp`
- `test_fetch_topic_relevant_communities_uses_fixed_anchor_timestamp`
- `test_build_entity_sentiment_matrix_uses_fixed_anchor_timestamp`

## 验证结果

### 代码与回归
- AST：
  - `backend/scripts/report/generate_t1_market_report.py`
  - `backend/app/services/analysis/t1_stats.py`
  - 新增/修改测试文件
  - 通过
- 定向回归：
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_report_logic.py tests/services/analysis/test_t1_stats_determinism.py tests/services/analysis/test_facts_v2_quality_gate.py tests/services/analysis/test_facts_v2_midstream.py -q`
  - 结果：`40 passed`
- 质量门禁：
  - `SKIP_DB_RESET=1 make test-quality-gate`
  - 结果：`24 passed`

### 确定性双跑验证（关键）
- 验证命令：
  - `PYTHONPATH=backend python backend/scripts/report/generate_t1_market_report.py --topic "robot vacuum cleaner" --mode market_insight --skip-llm --days 365 --anchor-ts "2026-03-12T03:00:00+00:00"`
- 两次运行导出的文件：
  - `backend/scripts/reports/local-acceptance/facts_v2_ec38aebc-dadd-5d79-b9e0-6f2290d51ff3.json`
- 第一次复制后的哈希：
  - `90905bcc1907a8bb99ebc271a8193bec72d7c3d5`
- 第二次复制后的哈希：
  - `90905bcc1907a8bb99ebc271a8193bec72d7c3d5`
- `diff -u <(python3 -m json.tool /tmp/fix_run1.json) <(python3 -m json.tool /tmp/fix_run2.json)`：
  - **0 diff**

## 这轮收口后的结论

- FIX-8 已收口：确定性模式下不再走语义扩展 LLM。
- FIX-9 已收口：`t1_stats.py` 主链时间窗不再依赖 `NOW()`。
- FIX-10 已收口：确定性模式下 persona / brand 两处残余 LLM 已跳过。
- FIX-11 已收口：`validate_facts_v2.py` 断路径不再报错。

## 额外发现

- `anchor_keywords` 的打印顺序依旧可能因为 set 转 list 而变化，但这轮双跑证明它没有再影响最终 `facts_v2` 输出。
- 当前 `robot vacuum cleaner` 的双跑已经实现文件级一致，说明这轮 fix 至少把“确定性模式主链”收住了。

## 下一步建议

1. 按同样方法，把 Phase240 原始 8 个领域命令矩阵完整重跑一遍。
2. 如果 8/8 全绿，再把这套“确定性模式”固化成回归脚本或 Make 目标，避免以后再回退。
