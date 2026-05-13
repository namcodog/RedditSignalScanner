# Phase 204 - llm-label Skill 落地

## 执行范围
- 新增 Codex skill：llm-label
- 固化离线打标流程（导出→Agent→质检→导入→语义回流）

## 交付物
- Skill 文件：`/Users/hujia/.codex/skills/llm-label/SKILL.md`

## 关键口径
- 只用 `llm_label_prompt_version`（记录用），不使用报告 v9json prompt
- 默认 dev 数据库，禁止金库
- Schema 以 `backend/app/services/llm/labeling.py` 为准

## 差异说明
- 无

## Dry-run 验证
- 导出：posts 14 条，comments 0 条（comment_scores 未覆盖）
- 产出：client_llm_labels_posts.jsonl（14 条）
- 质检：schema/枚举/行数一致
- 导入：post_llm_labels 写入 14 条
- 语义回流：candidates 5118 / auto_approved 56 / pending 5062

## Comments 链路补齐
- data-score：comment_scores 处理 500 条
- 导出：comments 14 条
- 产出：client_llm_labels_comments.jsonl（14 条）
- 质检：schema/枚举/行数一致
- 导入：comment_llm_labels 写入 14 条
- 语义回流：candidates 5083 / auto_approved 13 / pending 5070
