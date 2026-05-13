# Phase 666 - Pack Supply Fix V1

## 发现了什么

- `paid-economics` 和 `tools-efficiency` 原先都不具备进入 pack 定向 `signal skill` 实验的条件：
  - `3/3` candidate 全部在 `signal input quality gate` 前被挡掉
- 根因不是 prompt，而是供给层：
  - 社区太泛
  - query 太泛
  - day/rising listing 噪音太重

## 是否需要修复

需要，而且已经按最小变更集修了：

- 缩社区
- 收 query
- 这两个 pack 只保留 `listing:top:week`

## 精确修复方法

### 本轮代码改动

- `backend/app/services/hotpost/topic_pack_scope_growth.py`
  - `paid-economics` 去掉 `marketing / shopify`
  - 换成更垂直的广告社区和更贴近投放经济判断的 query
- `backend/app/services/hotpost/topic_pack_scope_ai.py`
  - `tools-efficiency` 去掉 `ChatGPT / productivity`
  - 换成更贴近 workflow 摩擦的社区和 query
- `backend/app/services/hotpost/reddit_search_spec_builder.py`
  - `paid-economics / tools-efficiency` 只保留 `listing:top:week`
  - 其他 pack 继续沿用原本 listing 组合
- 新增 pack 定向 builder：
  - `backend/app/services/hotpost/signal_pack_eval_builder.py`

### 测试

```bash
SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_reddit_search_spec_builder.py backend/tests/services/hotpost/test_source_scope_catalog.py backend/tests/services/hotpost/test_source_scope_candidate_collector.py backend/tests/services/hotpost/test_signal_pack_eval_builder.py -q
```

- 结果：`12 passed`

### 真实 collect 验证

- `business-growth-ops / paid-economics`
  - 通过 gate：`2`
  - 被挡：`1`
  - judge：`0 pass / 2 fail`
- `ai-automation / tools-efficiency`
  - 通过 gate：`1`
  - 被挡：`2`
  - judge：`0 pass / 1 fail`

## 下一步系统性的计划是什么

1. `paid-economics`
   - 现在已经具备进入 pack 定向 `signal skill` 实验的最低条件
   - 下一步可以专门针对它做写法优化
2. `tools-efficiency`
   - 供给仍然偏弱
   - 先继续补输入供给，不急着进 skill 实验
3. 不放松 `signal input quality gate`
4. 不回到全局 prompt 调优

## 这次执行的价值是什么

这轮把“最差 pack 完全进不了实验盘子”的状态，推进成了：

- `paid-economics` 已经能产出可写样本
- `tools-efficiency` 也不再是全灭

也就是说，主线开始从“纯供给修复”推进到：

- `paid-economics` 可进入 pack 级 skill 优化
- `tools-efficiency` 继续修供给
