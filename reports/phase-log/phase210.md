# Phase 210 - 365 天窗口 + noise 抽样候选导出

## 目标
- 按 365 天窗口导出 LLM 候选（core/lab 全量 + noise 高互动抽样）

## 执行
- `PYTHONPATH=. python scripts/export_llm_label_candidates.py --export-all --include-noise --noise-ratio 0.1 --noise-min-score 20 --noise-min-comments 10 --lookback-days 365 --post-limit 0 --comment-limit 0 --output-dir ../reports/llm-client/agent-365d`

## 结果
- 输出文件：
  - reports/llm-client/agent-365d/posts_batch_001.jsonl (1104)
  - reports/llm-client/agent-365d/comments_batch_001.jsonl (227091)
