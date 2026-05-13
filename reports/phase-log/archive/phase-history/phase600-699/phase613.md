# Phase 613 - Platform Conversion Rant 前置阶段假设进入抓取层

## 本轮目标

不是继续把 `118 -> 1` 当成正常结果，而是把“成交前转化阻力”的阶段判断更早写进抓取层，减少后筛救火。

## 完成内容

### 1. `ProblemFrame` 正式前置阶段假设

- 在 `platform_conversion_friction` 下，若 query 明确带有点击/跟踪/checkout 等成交前阶段信号：
  - `tiktok ads no sales`
  - `tiktok ads tracking conversion`
  - `tiktok ads checkout conversion`
- 不再只靠后面的 `retrieval_precision` 去砍噪音。

涉及文件：

- `backend/app/services/hotpost/problem_frame.py`
- `backend/app/services/hotpost/query_planner.py`

### 2. query budget 改成 family 级，而不是全局 rant 级

- `platform_conversion_friction` 现在允许保留 3 条 query parts
- 不影响其他 rant family，也不去改全局配置

涉及文件：

- `backend/app/services/hotpost/query_planner.py`
- `backend/app/services/hotpost/search_workflow.py`

### 3. 执行排序把优先级收回给 `ProblemFrame`

- `split_search_queries(...)` 生成的拆句候选，不再和 family 自己生成的 hypotheses 抢优先级
- `platform_conversion_friction` 下：
  - 成交前阶段信号优先
  - `seller / no orders` 这类更粗的句子往后

涉及文件：

- `backend/app/services/hotpost/search_workflow.py`

### 4. 测试口径同步校正

- 新增/修正：
  - `test_hotpost_problem_frame.py`
  - `test_hotpost_query_planner.py`
  - `test_hotpost_search_workflow.py`
- 核心断言：
  - family 前置阶段假设存在
  - planner 保留 3 条
  - workflow 初始执行确实先跑这 3 条

## 验证结果

### 定向回归

- `tests/services/hotpost/test_hotpost_problem_frame.py`
- `tests/services/hotpost/test_hotpost_query_planner.py`
- `tests/services/hotpost/test_hotpost_search_workflow.py`

结果：

- `37 passed`

### 全量回归

- `tests/services/hotpost`
- `tests/services/infrastructure/test_reddit_client_proxy.py`

结果：

- `218 passed`

## 结果判断

这轮的价值不是“又把某条 query 调顺了”，而是把 `platform conversion rant` 这类问题进一步收成了系统设计：

- family 自己定义阶段假设
- planner 给 family 足够的 query budget
- workflow 执行顺序服从 family hypothesis

也就是说：

- 不再只是后筛更狠
- 开始变成前抓更准

## 当前结论

方向仍然是对的，没有回到兜底或单题 patch。

但这轮也暴露了一个独立问题：

- 通过 API 跑 uncached live 时，入口翻译/环境噪音仍会污染最终结果
- 所以当前验收更可信的是：
  - contract 回归
  - full regression
  - 以及受控 resolution 下的算法层验证

## 下一步

下一步继续只打算法，不补 prompt，不补页面：

1. 把 `platform conversion rant` 的 benchmark 再扩几种表达方式
2. 对比：
   - raw_posts / filtered_posts
   - top_titles 纯度
3. 再决定是否继续把“阶段判断”进一步前移到 subreddit scout
