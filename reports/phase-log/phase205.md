# Phase 205 - 有效池缺口导出（Posts 全量补齐）

## 执行范围
- dev 库只读
- 导出有效池缺口（posts core/lab 全量）

## 变更
- export 脚本支持仅导出 posts 或 comments
  - backend/scripts/export_llm_label_candidates.py（新增 --posts-only / --comments-only）

## 导出命令
- PYTHONPATH=backend python backend/scripts/export_llm_label_candidates.py \
  --export-all --posts-only --post-limit 0 --comment-limit 0 \
  --lookback-days 36500 --output-dir reports/llm-client/missing

## 导出结果
- posts 缺口：77,178
- 文件路径：reports/llm-client/missing/posts_batch_001.jsonl

## 备注
- 口径：有效池（core/lab）全量
- comments 已超过 30% 覆盖率，本次不导出

## Comments 缺口补量（目标 60% 覆盖率）
- 目标覆盖率：60%
- 当前已标：286,782
- 目标数量：457,435
- 缺口：170,653

### 导出命令
- PYTHONPATH=backend python backend/scripts/export_llm_label_candidates.py \
  --export-all --comments-only --comment-limit 170653 \
  --lookback-days 36500 --output-dir reports/llm-client/missing

### 导出结果
- comments 缺口：170,653
- 文件路径：reports/llm-client/missing/comments_batch_001.jsonl
