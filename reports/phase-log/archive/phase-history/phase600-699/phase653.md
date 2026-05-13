# Phase 653 - Suggestion 实战验证：当前仍会降回信号

## 结果

这轮拿当前 2 条 suggestion 做了真实实战验证：

- `suggestion-ecommerce-sellers-ac0954d331`
- `suggestion-ai-automation-8f0a4a210e`

都已经能成功进入：

- `seed-draft-from-suggestion`
- `generate_card_content`
- `save_draft`

但最终结果不是 `write` 拆解草稿，而是都**自动降回了 `validate` 信号草稿**。

## 发现

这不是“文案写得不够深”，而是当前门槛不对齐：

- suggestion 层只要求：
  - 至少 2 个帖子
  - 至少 2 条 quote
- 但 breakdown 生成层要求：
  - `thread_count >= 2`
  - `len(evidence_quotes) >= 3`
  - `thesis`
  - `quote_pack >= 2`
  - `community_count >= 2 or thread_count >= 3`

所以当前这 2 条 suggestion 虽然够当“可疑拆解候选”，
但还不够真正升成 `🔍 拆解`。

## 实战产物

磁盘里实际落下来的两张草稿：

- `draft-group-ecommerce-sellers-ac0954d331`
- `draft-group-ai-automation-8f0a4a210e`

两张都是：

- `card_type = validate`

说明当前 suggestion 的产品语义更像：

- 值得尝试组卡

而不是：

- 已经够格生成拆解

## 当前判断

这轮验证把一个结构问题暴露出来了：

**suggestion 门槛 < breakdown 门槛**

所以现在会出现：

- suggestion 看起来成立
- 真进生成链时又降回信号

这会让运营以为“可以拆”，但系统最后说“不够拆”。

后续最值钱的修法不是润文案，而是先把 suggestion 规则和 breakdown 规则重新对齐。
