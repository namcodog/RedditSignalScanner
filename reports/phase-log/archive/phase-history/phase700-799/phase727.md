# Phase 727 - 候选面继续放宽，前台卡片增至 80

## 本轮结果

- 继续沿着“先把进口做厚，再严发”的方向推进，没有回到旧的窄输入世界。
- `AI / 电商 / 增长` 三条线都继续走新 YAML 合同和现有 `signal-ops / hot-ops`。
- 前台已发布卡片从 `75 -> 80`。

## 关键验证

### 1. 电商 cluster 串味问题收紧

- `selection-signals` 不再把 `CatAdvice / dogs / Pets` 这类照护求助社区当成主力搜索入口。
- `cluster_segments` 已验证有效：
  - 宠物清洁类 query 不再喷到 `ManyBaggers` 这类 EDC 社区。

相关测试：

- [test_source_scope_catalog.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_source_scope_catalog.py)
- [test_reddit_search_spec_builder.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_reddit_search_spec_builder.py)
- [test_source_scope_candidate_collector.py](/Users/hujia/Desktop/RedditSignalScanner/backend/tests/services/hotpost/test_source_scope_candidate_collector.py)

结果：

- `19 passed`

### 2. collect 放宽后，候选面已继续抬高

重跑后当前候选池已经明显比前几轮厚，且电商候选从“宠物求助帖”转向了更多真实消费/卖家/替代场景。

但也暴露了一个新的真实瓶颈：

- `spec` 数量已经来到：
  - `ai-automation = 1184`
  - `ecommerce-sellers = 1041`
  - `business-growth-ops = 2435`
- collect 能跑，但已经明显变慢。

结论：

- 方向对了
- 但下一步要收的是 **spec 预算和优先级**，不是再把输入缩回去

## 本轮新发卡片

这轮新增 `5` 张 signal 卡：

- `工具还没用上，用户先在取消试用这一步被 SEMrush 收走 211 美元。`
- `Shop 广告一插手分发，卖家开始怀疑它是在放大广告费，不是在放大订单。`
- `买小套锅时，评论区先筛的不是价格，而是哪家锅真的能熬很多年。`
- `一块大方巾开始替掉旅行毛巾和收纳袋，轻装用户在重新算一物多用的账。`
- `讨论开始担心的不是 AI 会不会找洞，而是补丁流程会不会先跟不上。`

mini snapshot 已推送：

- `release-0ba0055dfd3f`
- `card_count = 80`

## 当前盘面

- 已发布总数：`80`
- lane：
  - `signal = 77`
  - `hot = 3`
- 领域：
  - `AI 与自动化 = 29`
  - `商业增长与运营 = 29`
  - `电商与卖家 = 22`

## 下一步

1. 继续跑 collect 和出卡，不回到旧世界。
2. 单独收 `hot` lane 的供给，争取自然长出第 `4 / 5` 张真正像样的热点卡。
3. 开始收 `spec` 预算和优先级，让“覆盖够宽”和“运行够快”同时成立。
