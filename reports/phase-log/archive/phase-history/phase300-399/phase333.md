# Phase 333 - 第三轮：hotpost 证据收集 workflow 收口

## 1. 发现了什么？

- `HotpostService.search()` 里还缠着一整段 live 主链重逻辑：
  - 建议社区
  - 拉帖
  - 低相关过滤
  - 拉评论
  - 情绪/分类/置信度汇总
- 这段逻辑一边取数据，一边自己组装证据结果，导致 `search()` 仍然过重。
- 另外还照出了一个真实漂移点：
  - `summary_result = await self._maybe_llm_summary(..., community_distribution=community_distribution)` 这里引用了未定义变量。
  - 以前测试没卡住这条 live 路径，所以这个问题一直没被正式锁住。

## 2. 是否需要修复？

- 需要，而且这一步已经修完。
- 这次没有改数据库表结构，没有新增 migration。
- 改的是 `hotpost` 模块里的 live 证据收集边界、service 编排职责和测试门禁。

## 3. 精确修复方法？

### 3.1 新增独立 workflow

新增：

- `backend/app/services/hotpost/evidence_collection_workflow.py`

正式收了：

- `HotpostEvidenceCollectionInput`
- `HotpostEvidenceCollectionDeps`
- `HotpostEvidenceCollectionResult`
- `collect_hotpost_evidence(...)`

这条 workflow 统一承接：

- 缺省 subreddit 建议
- subreddit/global 搜索
- 帖子去重
- relevance filter
- top posts 构建
- top comments 拉取
- `sentiment_overview / confidence / community_distribution`
- `pain_points / opportunities / me_too_count`

### 3.2 收薄 `HotpostService.search()`

修改：

- `backend/app/services/hotpost/service.py`

`search()` 不再自己手工维护整条 live 证据收集链，而是：

1. 解析 query 和 cache key
2. 调 `collect_hotpost_evidence(...)`
3. 再继续做 summary / report / response / persistence

顺手把 `community_distribution` 改成直接吃 workflow 返回值，彻底去掉未定义变量漂移点。

### 3.3 补测试并锁合同

新增测试：

- `backend/tests/services/hotpost/test_evidence_collection_workflow.py`
- `backend/tests/services/hotpost/test_hotpost_search_service.py`

本轮新增门禁覆盖：

- 缺省 subreddit 建议 + community distribution 汇总
- opportunity 模式低相关过滤
- `search()` live 路径必须把 `community_distribution` 正确传进 summary workflow

## 4. 当前结果

- `backend/app/services/hotpost/service.py`
  - 当前降到 `720` 行
- 本轮 `git diff --stat`（核心 service）：
  - `234 insertions(+), 442 deletions(-)`

大白话：

- `hotpost search()` 现在更像编排层了
- “怎么收集证据”开始有自己的独立齿轮
- `community_distribution` 这类容易漂的 live 口径，现在开始有正式真相源

## 5. 验证

### 定向门禁

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/hotpost/test_evidence_collection_workflow.py \
  tests/services/hotpost/test_hotpost_search_service.py -q
```

结果：

- `3 passed`

### hotpost 整组回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost -q
```

结果：

- `58 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/hotpost/service.py \
  app/services/hotpost/evidence_collection_workflow.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 6. 下一步系统性的计划是什么？

- 第三轮继续按既定节奏推进，不换打法。
- 下一刀优先继续专打剩余最重的几块：
  1. `facts / 报告模块`
  2. `数据采集模块`
  3. `语义 / 标签模块`

继续沿同一条线推进：

- 主服务继续变薄
- task 壳继续变薄
- workflow / service 继续独立
- 单一真相源继续做硬

## 7. 这次执行的价值是什么？达到了什么目的？

- 这次不是修一个小 bug，而是把 `hotpost` 里 live 主链最重的一段真正拆成独立 workflow。
- 系统又往你要的方向推进了一步：
  - 各模块职责更清楚
  - 通过统一接口协同
  - 彼此少牵连
  - 整条链路更顺、更可控

一句大白话收口：

- `hotpost` 现在不只是“能给结果”，而是“证据怎么收集”也开始说同一种话了。
