# Phase 342 - 第三轮继续推进：Hotpost Report Workflow 独立化

## 本轮目标

继续第三轮结构性打磨，把 `HotpostService.search()` 里还缠着的 `hotpost report` LLM 编排链拆成独立 workflow，让主服务继续变薄，边界继续收紧。

## 发现的问题

- `backend/app/services/hotpost/service.py` 里的 `search()` 之前还在自己背完整 `report llm` 子链：
  - `ENABLE_HOTPOST_LLM_REPORT` 开关判断
  - API key 检查
  - 无证据早退
  - `posts/comments` payload 构造
  - `generate_hotpost_llm_report(...)` 调用
- 这导致 `HotpostService` 继续同时承担：
  - live 搜索编排
  - 响应组装
  - report llm 子流程
- 这种写法会让后面改：
  - 开关口径
  - report payload
  - llm client 调用
  - degraded reason
  时继续牵动主服务。

## 修复动作

### 1. 新增独立 workflow

新增：

- `backend/app/services/hotpost/report_workflow.py`

正式收了：

- `HotpostReportWorkflowInput`
- `HotpostReportWorkflowDeps`
- `_env_flag(...)`
- `build_hotpost_report_result(...)`

这条 workflow 现在统一承接：

- report llm 开关判断
- API key 检查
- 无 evidence 早退
- `max_tokens / temperature` 环境变量读取
- `posts_data / comments_data` 构造
- `generate_hotpost_llm_report(...)` 调用

### 2. 收薄 HotpostService

修改：

- `backend/app/services/hotpost/service.py`

`search()` 不再自己手工维护整条 `llm_report_result` 分支，改成统一委托给：

- `build_hotpost_report_result(...)`

### 3. 补测试并锁新边界

新增：

- `backend/tests/services/hotpost/test_hotpost_report_workflow.py`

覆盖：

- 开关关闭时返回 `report_llm_disabled`
- 缺少 API key 时返回 `missing_api_key`
- 正常路径会正确构造 payload 并调用 generator

同时调整：

- `backend/tests/services/hotpost/test_hotpost_search_service.py`

把 seam 从旧的：

- `generate_hotpost_llm_report`

改到新的：

- `build_hotpost_report_result`

## 结果

- `HotpostService.search()` 继续变薄，不再亲手维护 `report llm` 子链
- `hotpost report` 的 enable/disable、payload 组装、degraded 原因开始有独立真相源
- 后面再改 report llm 这条链时，不容易继续把主服务拖重

## 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/hotpost/test_hotpost_report_workflow.py \
  tests/services/hotpost/test_hotpost_search_service.py \
  tests/services/hotpost/test_hotpost_report_llm.py -q
```

结果：

- `8 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/hotpost/report_workflow.py \
  app/services/hotpost/service.py \
  tests/services/hotpost/test_hotpost_report_workflow.py \
  tests/services/hotpost/test_hotpost_search_service.py
```

结果：

- 通过

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 当前判断

这一步是第三轮里一刀真正值钱的结构性收口：

- `hotpost` 主服务继续变薄
- `report llm` 子链开始有独立齿轮
- 模块边界继续往“职责清楚、统一接口协同、彼此少牵连”推进

## 下一步

继续第三轮，不换打法，优先继续专打剩余最重的耦合点：

1. `facts / 报告模块`
2. `数据采集模块`
3. `语义 / 标签模块`
