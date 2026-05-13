# Phase 355 - hotpost search 总装配链独立 workflow

## 时间
- 2026-03-17

## 本轮目标
- 收掉 `HotpostService.search(...)` 里还偏重的总装配链
- 让 `HotpostService` 继续变薄，同时保住 `service.search(...)` 现有入口合同

## 发现了什么
- `HotpostService.search(...)` 之前虽然已经拆出：
  - evidence collection
  - summary workflow
  - report workflow
  - persistence workflow
- 但主链自己还在背：
  - mode / time_filter / sort 解析
  - query resolve
  - cache hit fast path
  - query row + queue tracker 生命周期
  - live path 下 evidence / summary / report / response / persistence 串联
- 这会让 `service.search(...)` 继续像半个“大总管”。

## 这次做了什么
- 新增独立 workflow：
  - `backend/app/services/hotpost/search_workflow.py`
- 正式收了：
  - `HotpostSearchWorkflowInput`
  - `HotpostSearchWorkflowDeps`
  - `HotpostSearchWorkflowResult`
  - `run_hotpost_search_workflow(...)`
- 收薄入口：
  - `backend/app/services/hotpost/service.py`
  - `search(...)` 现在只负责：
    1. 构建 query translation 的 llm client
    2. 组装 workflow input / deps
    3. 调 workflow
    4. 返回 `response`
- 新增定向测试：
  - `backend/tests/services/hotpost/test_hotpost_search_workflow.py`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost/test_hotpost_search_workflow.py tests/services/hotpost/test_hotpost_search_service.py tests/api/test_hotpost.py -q`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/hotpost -q`
- `SKIP_DB_RESET=1 make test-quality-gate`

## 结果
- `HotpostService.search(...)` 开始更像真正的编排入口
- cache hit path 和 live path 都有了正式 workflow 真相源
- 现有 service / API 调用口径保持不变，旧 seam 没被砍断

## 下一步
- 继续第三轮，优先专打剩余最重的几块：
  1. `facts / 报告模块`
  2. `数据采集模块`
  3. `语义 / 标签模块`
