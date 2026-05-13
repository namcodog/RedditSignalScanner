# Phase 616 - Hotpost Rant 中文比较抱怨 Query Contract 第一刀

## 时间
- 2026-03-30

## 目标
- 先把 `rant` 的中文比较抱怨入口收正
- 保住“在骂谁、和谁比”的 query 锚点

## 发现了什么？

### 1. 当前主问题不是没比较，而是比较对象没被稳定顶住
- 之前 comparison rant 在 `query_en` 层有时还能留下比较关系
- 但 `keywords` 前排会被英文解释词污染
- 结果就是：
  - 对象词不稳定
  - 比较类 query 很容易被后续链路继续带偏

### 2. `hotpost` 本身不依赖 Postgres
- 这次测试碰 DB，不是产品链路依赖了库
- 是 `backend/tests/conftest.py` 里的全局 `reset_database` fixture 在跑 pytest 时自动触发

## 是否需要修复？
- 需要。
- 这轮只修 query contract，不顺手扩到样本层和页面层。

## 精确修复方法

### 一、comparison rant 改成“原问题对象优先”
- `backend/app/services/hotpost/query_resolver.py`
  - 新增 comparison rant 规范化：
    - 原问题对象优先
    - `complaints` 锚点第二
    - 解释词靠后

### 二、cache 与 llm 统一收口
- cache 命中不再绕过 comparison normalization
- llm 新结果也统一走同一套规范化

### 三、prompt 明确保留比较关系
- 要求保留：
  - `vs / compare / better than / worse than`
  - 双方对象

### 四、补测试把边界卡死
- `backend/tests/services/hotpost/test_hotpost_query_resolver.py`
  - 新增中文比较抱怨测试
  - 新增 cache 命中下的比较抱怨测试

## 下一步系统性计划

1. 第二刀只打：
   - `evidence truth`
   - “样本不足”诚实判定
2. 把 `raw_hits / relevant_hits / voice_hits` 拆开验证
3. 不回头补 summary-first 表达

## 这次执行的价值是什么？
- 第一刀已经把 `rant` 最容易带偏的中文入口收住了。
- 用户输入“我觉得 A 比 B 好，B 根本不好用”这类话时，系统终于开始先理解“谁在骂谁”，而不是先生成一堆看起来正确的英文废话。
