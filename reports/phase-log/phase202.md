# Phase 202 - LLM 客户端打标数据包准备

## 执行范围
- dev 库数据导出（只读）
- 客户端打标数据包准备

## 交付物
- 导出脚本：backend/scripts/export_llm_label_candidates.py
- 导出文件：
  - reports/llm-client/posts_batch_001.jsonl
  - reports/llm-client/comments_batch_001.jsonl

## 最新导出状态
- posts: 129,079
- comments: 270,675

## 备注
- comments 候选为空：需要先跑 data-score 生成 comment_scores，再导出

## 本次标注产出
- 输出文件：
  - client_llm_labels_posts.jsonl（70）
  - client_llm_labels_comments.jsonl（70）

## 差异说明
- 无

## 2026-01-31 规则修订后重跑
- 依据新规则批量重打标（全量文件）：
  - client_llm_labels_posts.jsonl（129079）
  - client_llm_labels_comments.jsonl（270675）
- 说明：输出为规则化自动标注版本

## 2026-02-01 新规则重跑（严格门禁）
- 依据最新硬性规则全量重打标：
  - client_llm_labels_posts.jsonl（129079）
  - client_llm_labels_comments.jsonl（270675）
- 门禁校验通过：枚举/标签非空/分数范围/行数一致

## 2026-02-01 缺口补标（missing posts）
- 输入：reports/llm-client/missing/posts_batch_001.jsonl（77178）
- 输出：client_llm_labels_posts_missing.jsonl（77178）
- 门禁校验通过：枚举/标签非空/分数范围/行数一致

## 2026-02-01 缺口补标（missing comments）
- 输入：reports/llm-client/missing/comments_batch_001.jsonl（170653）
- 输出：client_llm_labels_comments_missing.jsonl（170653）
- 门禁校验通过：枚举/标签非空/分数范围/行数一致

## 2026-02-01 空标签补标（empty tags posts）
- 输入：reports/llm-client/empty-tags/posts_empty_tags_batch_001.jsonl（6648）
- 输出：client_llm_labels_posts_emptytags.jsonl（6648）
- 门禁校验通过：枚举/范围/行数一致

## 2026-02-01 365d agent 批次
- 输入：reports/llm-client/agent-365d/posts_batch_001.jsonl（1104）
- 输出：client_llm_labels_posts.jsonl（1104）
- 输入：reports/llm-client/agent-365d/comments_batch_001.jsonl（227091）
- 输出：client_llm_labels_comments.jsonl（227091）
- 门禁校验通过：枚举/标签非空/分数范围/行数一致
