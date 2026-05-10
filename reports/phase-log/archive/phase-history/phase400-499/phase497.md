# Phase 497 - hotpost 前端展示口径收口

## 时间
- 2026-03-27

## 目标
- 收口前端反馈的 4 个 hotpost 展示问题，避免“后端结果正常但页面解释偏掉”。

## 执行内容

### 1) 统一 mode 中文映射
- 文件：
  - `frontend/src/lib/product-surface.ts`
- 调整为：
  - `trending -> 热点追踪`
  - `rant -> 痛点挖掘`
  - `opportunity -> 机会发现`
- 影响面：
  - hotpost 结果页 hero
  - 结果页 badge / 说明文案

### 2) 收 confidence 中文口径
- 文件：
  - `frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - `frontend/src/lib/product-surface.ts`
- 调整为：
  - `high -> ✔ 信号可靠`
  - `medium -> ⚠ 信号一般`
  - `low -> △ 信号有限`
- 同步调整结果页 badge 色阶，让高置信度不再继续用旧的“信号扎实/方向已浮现/先看线索”口径。

### 3) 收 `time_trend` 中文映射
- 文件：
  - `frontend/src/pages/hotpost/HotPostResultPage.tsx`
- 新增兼容映射：
  - `explosive/exploding -> 爆发中 NEW`
  - `rising -> 上升中 ↑`
  - `stable/sustained -> 持续热度 ↗`
  - `declining -> 下降中 ↓`
- 同时兼容旧中文值，避免历史结果页显示飘忽。

### 4) 补 `top_quotes` 为空时的 quote 降级
- 文件：
  - `frontend/src/types/hotpost.ts`
  - `frontend/src/pages/hotpost/HotPostResultPage.tsx`
- 动作：
  - 前端类型层补 `top_quotes`
  - 结果页新增“代表原话”区域
  - 优先显示 `top_quotes`
  - 若为空，则自动从以下证据字段回退抽取：
    - `topics[].evidence[].key_quote`
    - `pain_points[].evidence[].key_quote`
    - `unmet_needs[].evidence[].key_quote`
    - `migration_intent.key_quote`
    - 竞品引用字段
- 额外收口：
  - rant 模式下 `sample_quotes` 为空时，也会回退到 `pain_points[].evidence[].key_quote`

## 测试与验证

### 前端定向测试
- `npm test -- --run src/pages/__tests__/HotPostResultPage.surface.test.tsx`
- 结果：
  - `7 passed`
- 新增覆盖：
  - mode/confidence/time_trend 新口径
  - `top_quotes=[]` 时回退到 `topics[].evidence[].key_quote`
  - rant 模式 `sample_quotes=[]` 时回退到 `pain_points[].evidence[].key_quote`

### 前端构建
- `npm run build`
- 结果：
  - 构建通过

## 四问回顾
1. 发现了什么？
- hotpost 现在主链已经能正常跑结果，但前端展示层还有几处“口径没收住”的问题：
  - mode 中文名不统一
  - confidence 还是旧文案
  - `time_trend` 英文值直接透传
  - `top_quotes` 为空时没有自动兜底

2. 是否需要修复？
- 需要。否则用户会把“展示问题”误读成“结果问题”。

3. 精确修复方法？
- 收 mode/confidence/time_trend 的前端映射；
- 给结果页补 quote 抽取与降级；
- 用前端测试固定新口径，防止后续再飘回去。

4. 下一步系统性计划是什么？
- 后续再有 hotpost 字段调整，优先先补 surface test，再改页面；
- 把展示口径也当成合同，而不是靠人工记忆。

5. 这次执行的价值是什么？
- hotpost 现在不只是“能启动、能拿结果”，而且“结果页解释口径稳定、缺字段时也不会塌”。
