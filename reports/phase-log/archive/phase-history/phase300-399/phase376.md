# Phase 376 - 第三轮大包推进：HotpostService helper 与 deps 装配成组收口

## 1. 发现了什么？

这次收的是 `hotpost` 模块里剩下最重的一整包：

- helper 逻辑
- search workflow deps 装配

之前 `backend/app/services/hotpost/service.py` 还同时背着：

- mode / time_filter / sort 判定
- query split
- rate budget
- subreddit 分页抓取
- comments 抓取
- signals / sentiment / post / pain_points / confidence
- summary fallback
- search workflow deps 装配

大白话说：

- `HotpostService` 虽然已经比最早薄很多了
- 但还在一边当入口，一边自己亲手跑整组 helper 和 wiring

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增统一 runtime 层

新增：

- `backend/app/services/hotpost/hotpost_runtime.py`

正式收了：

- `resolve_hotpost_mode(...)`
- `split_hotpost_search_queries(...)`
- `resolve_hotpost_time_filter(...)`
- `resolve_hotpost_sort(...)`
- `acquire_hotpost_rate_budget(...)`
- `search_hotpost_subreddit_posts(...)`
- `fetch_hotpost_comments(...)`
- `select_hotpost_signals(...)`
- `resolve_hotpost_sentiment_label(...)`
- `build_hotpost_post(...)`
- `build_hotpost_pain_points(...)`
- `resolve_hotpost_confidence_level(...)`
- `maybe_build_hotpost_llm_summary(...)`
- `build_hotpost_fallback_text(...)`

### 3.2 新增 deps factory

新增：

- `backend/app/services/hotpost/hotpost_deps_factory.py`

正式收了：

- `HotpostSearchDepsFactoryInput`
- `build_hotpost_search_deps(...)`
- `build_hotpost_response_status(...)`
- `build_hotpost_debug_contract(...)`

### 3.3 收薄 HotpostService

调整：

- `backend/app/services/hotpost/service.py`

现在 `HotpostService` 里的同名方法大多已经收成薄 wrapper：

- 继续保留旧名字，兼容现有测试 patch seam
- 真正的 helper 逻辑已经回到 `hotpost_runtime.py`
- 真正的 search deps 装配已经回到 `hotpost_deps_factory.py`

一个很直观的结果：

- `service.py` 从 `536` 行，压到了现在的 `361` 行

### 3.4 补测试锁边界

新增：

- `backend/tests/services/hotpost/test_hotpost_runtime.py`
- `backend/tests/services/hotpost/test_hotpost_deps_factory.py`

并继续跑通：

- `backend/tests/services/hotpost/test_hotpost_search_service.py`
- `backend/tests/services/hotpost/test_hotpost_comments.py`
- `backend/tests/services/hotpost/test_hotpost_summary.py`
- `backend/tests/services/hotpost/test_hotpost_search_workflow.py`
- `backend/tests/services/hotpost/test_hotpost_report_workflow.py`
- `backend/tests/services/hotpost/test_evidence_collection_workflow.py`
- `backend/tests/services/hotpost/test_persistence_workflow.py`
- `backend/tests/services/hotpost/test_hotpost_schema.py`

## 4. 验证结果

### 4.1 成组定向回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/hotpost/test_hotpost_runtime.py \
  tests/services/hotpost/test_hotpost_deps_factory.py \
  tests/services/hotpost/test_hotpost_search_service.py \
  tests/services/hotpost/test_hotpost_comments.py \
  tests/services/hotpost/test_hotpost_summary.py \
  tests/services/hotpost/test_hotpost_search_workflow.py \
  tests/services/hotpost/test_hotpost_report_workflow.py \
  tests/services/hotpost/test_evidence_collection_workflow.py \
  tests/services/hotpost/test_persistence_workflow.py \
  tests/services/hotpost/test_hotpost_schema.py -q
```

结果：

- `20 passed`

### 4.2 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.3 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/hotpost/service.py \
  backend/app/services/hotpost/hotpost_runtime.py \
  backend/app/services/hotpost/hotpost_deps_factory.py \
  backend/tests/services/hotpost/test_hotpost_runtime.py \
  backend/tests/services/hotpost/test_hotpost_deps_factory.py
```

结果：

- 通过

## 5. 当前完成度判断

这一步之后，我的判断是：

- 第三轮完成度：约 `90%-91%`
- 系统整体完成度：约 `95%`

## 6. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `HotpostService` 里剩下的 helper 逻辑和 deps 装配，现在开始也有正式真相源了
- 后面再改：
  - query split
  - rate budget
  - comments 抓取
  - signals / sentiment
  - summary fallback
  - search wiring
  不容易再把主服务一起拖重

一句大白话总结：

- 这次把 `hotpost` 里剩下最重的一整包真正抽开了，第三轮已经很接近封板阶段。
