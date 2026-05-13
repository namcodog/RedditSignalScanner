# Phase 545 - 小程序 trending 详情页可理解度修正

## 时间
- 2026-03-28

## 背景
- `phase544` 已把小程序 `trending` 详情页从“字段页”升级成“分析页”。
- 但真实验收截图暴露了 4 个理解问题：
  1. 情绪概览太像系统标签
  2. 代表帖子里的命中说明是系统黑话
  3. `代表帖子` 和 `归档证据` 的区别不够清楚
  4. `下一步` 会重复用户输入词，缺少增量价值

## 本轮动作

### 1. 黑话翻译成人话
- 新增：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/content-helpers.ts`
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/sections.tsx`
- 把：
  - `直接命中`
  - `领域命中`
  - `社区语境待验证`
  翻译成用户能看懂的解释。

### 2. 情绪概览改成解释性文案
- 不再只裸露：
  - `正向 / 中性 / 负向`
- 改成：
  - 一句可读解释
  - 同时保留百分比
  - 明确“这里只看讨论语气，不代表观点对错”

### 3. 页面结构继续收口
- `归档证据` 改成 `用户原话`
- 增加 section guide：
  - `代表帖子` = 这波讨论从哪里起来
  - `用户原话` = 大家具体怎么说

### 4. 长文本统一做可读摘录
- 代表帖子正文补简摘并加 `...`
- 用户原话统一截断并加 `...`
- 字体改成和正文一致的阅读样式，不再像一整墙大段引文

### 5. 下一步只保留增量词
- `next_steps.suggested_keywords` 如果和用户 query 重复，就前端过滤掉
- 过滤后为空时，再回退到 `trending_keywords` 的增量词

## 验证
- 执行：
  - `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
- 结果：
  - `Compiled successfully`

## 结论
- 这轮不是继续扩字段，而是把页面从“能看”推进到“能看懂”。
- 当前 `trending` 详情页已经更像产品语言，而不是系统调试语言。

## 下一步
1. 在微信开发者工具里看真实体验，确认阅读节奏和链接动作都自然。
2. 如果稳定，再按同样口径改 `rant / opportunity`。
