# Phase 635

## 时间
- 2026-04-06

## 目标
- 修正详情页“去原讨论帖”这个假动作。
- 小程序内不再尝试跳原帖，改成复制帖子链接，并把链接显式展示给用户。

## 实现
- 详情页底部动作从“去原讨论帖”改成“复制帖子链接”。
- 点击后执行：
  - 复制 `source_link`
  - 显示“已复制帖子链接”
  - 在下方展开帖子链接展示块
- 链接展示块包含：
  - 标签：`帖子链接`
  - 状态：`已复制，可直接粘贴到浏览器打开`
  - 实际 URL 文本
- 用户原话区取消原先整块点击跳转，避免页面里继续保留隐性假动作。

## 改动文件
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.scss`

## 验证
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：通过

## 当前判断
- 详情页的原帖动作语义已经和小程序限制对齐。
- 现在用户不会再被“能跳过去”的假预期误导，而是直接拿到可复制的帖子链接。
