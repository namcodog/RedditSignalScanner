# Phase 207 - 空标签帖子导出与重标提示词

## 目标
- 导出空标签 posts 清单，供客户端重标
- 生成强约束重标 prompt

## 结果
- 输出文件：
  - reports/llm-client/empty-tags/posts_empty_tags_batch_001.jsonl
- 导出范围：
  - core/lab
  - value_score > 2.0
  - LLM 标签为空（pain/aspect/entities 全空）

## 说明
- 导出条数：6,648（dev）
