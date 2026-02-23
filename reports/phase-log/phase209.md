# Phase 209 - 265 天窗口 + noise 抽样候选导出

## 目标
- 按新口径导出 LLM 候选：core/lab 全量 + noise 高互动抽样
- 窗口扩展到 265 天

## 变更
- backend/scripts/export_llm_label_candidates.py
  - core/lab 不再使用 value_score > 2 的硬阈值
  - 新增 noise 抽样参数（ratio / min_score / min_comments）

## 执行
- `PYTHONPATH=. python scripts/export_llm_label_candidates.py --export-all --include-noise --noise-ratio 0.1 --noise-min-score 20 --noise-min-comments 10 --lookback-days 265 --post-limit 0 --comment-limit 0 --output-dir ../reports/llm-client/agent-265d`

## 结果
- 输出文件：
  - reports/llm-client/agent-265d/posts_batch_001.jsonl (1104)
  - reports/llm-client/agent-265d/comments_batch_001.jsonl (159837)
