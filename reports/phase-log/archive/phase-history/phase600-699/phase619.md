# Phase 619 - Hotpost Rant 第三刀 voices-first 页面合同落地

## 时间
- 2026-03-30

## 目标
- 把 `rant` 从 `summary-first` 收回成 `voices-first`
- 让页面默认顺序正式变成：
  - 代表原话
  - 核心骂点
  - 代表帖子
  - 对比 / 迁移
  - 范围说明 / 下一步

## 发现了什么？

### 1. 第三刀真正卡在页面合同
- 第二刀后，链路已经能说真话
- 但页面还是把 `pain_points / competitor / migration` 藏在“展开补充细节”后面
- 小程序 `friction` 页也还是旧顺序：
  - `summary -> 骂点 -> 迁移 -> 帖子 -> 原话`

### 2. `representative posts` 也没对齐痛点证据层
- Web 端原来只直接吃 `top_posts`
- 没优先拿 `pain_points[].evidence_posts`
- 这和验收标准里的“代表帖子优先来自真正支撑痛点的 evidence”不一致

## 是否需要修复？
- 需要。
- 这轮直接改页面合同，不继续扩算法。

## 精确修复方法

### 一、Web 端 `rant` 改成默认直出
- 文件：
  - `frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - `frontend/src/types/hotpost.ts`
- 关键调整：
  - `rant` 不再依赖“展开补充细节”
  - 新增 `representative posts` 收口：
    - `pain_points[].evidence_posts` 优先
    - `top_posts` 兜底
  - 新增 `范围说明与下一步` 区块：
    - `reliability_note`
    - `recommended_actions`
    - `suggested_keywords`
  - `top posts` 标题在 `rant` 模式下改成：
    - `代表帖子`

### 二、Web 端补第三刀验收测试
- 文件：
  - `frontend/src/pages/__tests__/HotPostResultPage.surface.test.tsx`
- 新增断言：
  - `rant` 默认可见原话 / 骂点 / 代表帖子 / 竞品 / 范围说明
  - 不再出现“展开补充细节”
  - 页面顺序符合第三刀合同

### 三、小程序 `friction` 页改同一顺序
- 文件：
  - `hotpost-mini/hotpost-mini-app/src/pages/friction/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/friction/sections.tsx`
- 关键调整：
  - 顺序改成：
    - `分析摘要`
    - `最刺耳的原话`
    - `核心骂点`
    - `代表帖子`
    - `对比与迁移`
    - `范围说明与下一步`
  - 小程序补回 `competitor_mentions` 展示
  - `范围说明` 直接展示 `reliability_note`

## 下一步系统性计划

1. 不开第四刀
2. 直接进入 `V1 收尾验收`
3. 用 4 到 6 个代表 query 跑端到端，确认：
   - 中文抱怨不带偏
   - 假样本不足消失
   - 第一屏先听到抱怨
   - 结果页一眼能看懂

## 这次执行的价值是什么？
- 第三刀完成后，`rant` 第一次真正像“听用户骂”的产品，而不是“系统先写总结，再把原话塞后面”。
- 这轮没再往底座加复杂度，只把用户最在意的展示合同收正了。
