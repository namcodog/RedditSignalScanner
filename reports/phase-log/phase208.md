# Phase 208 - 空标签 posts 回填与语义回流

## 目标
- 回填空标签 posts 的重标结果
- 触发语义候选回流并更新覆盖/质量统计

## 执行
- 回填：
  - `PYTHONPATH=. python scripts/import_client_llm_labels.py --posts ../client_llm_labels_posts_emptytags.jsonl --llm-version client-emptytags --prompt-version client-emptytags --model-name client-offline`
- 回流：
  - `make semantic-llm-sync`

## 结果
- 语义回流：`candidates=6375`, `auto_approved=317`, `pending=6058`
- 空标签占比（全量 LLM 标签表）：
  - posts: 9,925 / 393,126 = 2.52%
  - comments: 1,499 / 459,073 = 0.33%
- 覆盖率（lookback=90 天，core/lab + value_score>2）：
  - posts: 214,583 / 216,335 = 99.19%
  - comments: 280,349 / 280,416 = 99.98%
- 数据库：reddit_signal_scanner_dev（默认）
