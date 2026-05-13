# Phase 558 - Rant Prompt 分析合同收口

## 发现了什么？
- `痛点挖掘` 这条线当前最大的问题，不是后端没字段，而是 prompt 还偏“抱怨总结”，没有把“分析”写死。
- 后端其实已经支持这两类关键解释字段：
  - `top_quotes[].why_important`
  - `post_annotations[].why_important`
- 这意味着 `rant` 后面要做详情页时，不需要前端自己编分析文案，应该优先吃后端的解释字段。

## 是否需要修复？
- 需要。
- 这一步先不碰页面，先把 `prompt_rant.py` 的任务定义收紧，避免后面又退回模板式解释。

## 精确修复方法
- 更新 [prompt_rant.py](../../backend/app/services/hotpost/prompt_rant.py)
  - 要求关键帖子补：
    - `why_relevant`
    - `why_important`
  - 要求关键原话补：
    - `why_important`
  - 明确说明：
    - 不能只写“讨论很多”“抱怨不少”
    - 必须解释这条帖子/原话暴露了什么问题
    - 要判断它更像一次性吐槽、重复出现的真问题，还是已经出现流失信号
    - 要说明用户应该把它理解成体验问题、收入风险，还是迁移风险
- 更新 [test_hotpost_prompts.py](../../backend/tests/services/hotpost/test_hotpost_prompts.py)
  - 新增 `rant` prompt 合同测试，防止以后回退成浅解释

## 验证
- `pytest backend/tests/services/hotpost/test_hotpost_prompts.py -q`
- 结果：`5 passed`

## 下一步
- 按后端真实字段定义 `rant` 详情页结构：
  - `summary`
  - `pain_points`
  - `competitor_mentions`
  - `migration_intent`
  - `top_quotes`
  - `top_posts`
  - `next_steps`
- 再把小程序 [friction/index.tsx](../../hotpost-mini/hotpost-mini-app/src/pages/friction/index.tsx) 从 mock 换成真页面。
