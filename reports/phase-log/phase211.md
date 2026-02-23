# Phase 211 - 365 天批次回填与语义回流

## 目标
- 回填 365 天 agent 批次 labels（posts/comments）
- 回流语义库并统计覆盖/质量

## 执行
- 回填：
  - `PYTHONPATH=. python scripts/import_client_llm_labels.py --posts ../client_llm_labels_posts.jsonl --comments ../client_llm_labels_comments.jsonl --llm-version client-365d --prompt-version client-365d --model-name client-offline`
- 回流：
  - `make semantic-llm-sync`

## 结果
- 语义回流：`candidates=5322`, `auto_approved=223`, `pending=5099`
- 空标签占比（llm_version=client-365d）：
  - posts: 80 / 1104 = 7.25%
  - comments: 1945 / 227091 = 0.86%
- 空标签占比（llm_version=client-emptytags）：
  - posts: 18 / 6648 = 0.27%
- 覆盖率（365 天，core/lab）：
  - posts: 316,463 / 317,695 = 99.61%
  - comments: 638,314 / 638,314 = 100%
- 标签表规模（全量）：
  - post_llm_labels: 394,230
  - comment_llm_labels: 686,164
- 数据库：reddit_signal_scanner_dev（默认）
