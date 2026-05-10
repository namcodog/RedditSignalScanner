# Phase 357 - ReportService 请求链独立 workflow

## 时间
- 2026-03-17

## 本轮目标
- 收掉 `ReportService.get_report(...)` 里还偏重的完整请求链
- 让 `ReportService` 继续变薄，同时保住 `get_report(...)` 现有入口合同

## 发现了什么
- `ReportService.get_report(...)` 虽然前面已经拆掉不少重活，但主链自己还在背：
  - request context 加载
  - cache hit fast path
  - analysis payload 校验
  - assembly workflow 调用
  - cache 回写
- 这会让 `ReportService` 继续像半个“大总管”。

## 这次做了什么
- 新增独立 workflow：
  - `backend/app/services/report/report_request_workflow.py`
- 正式收了：
  - `ReportRequestWorkflowInput`
  - `ReportRequestWorkflowDeps`
  - `ReportRequestWorkflowResult`
  - `run_report_request_workflow(...)`
- 收薄入口：
  - `backend/app/services/report/report_service.py`
  - `get_report(...)` 现在只负责：
    1. 读 inline llm 开关
    2. 组装 workflow deps
    3. 调 workflow
    4. 返回 payload
- 新增定向测试：
  - `backend/tests/services/report/test_report_request_workflow.py`

## 验证
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report/test_report_request_workflow.py tests/services/report/test_report_service.py -q`
- `cd backend && python -m py_compile app/services/report/report_request_workflow.py app/services/report/report_service.py`
- `SKIP_DB_RESET=1 make test-quality-gate`

## 结果
- `ReportService.get_report(...)` 开始更像真正的薄入口
- request context / cache / validate / assembly 这条完整请求链开始有自己的正式齿轮
- 现有 service / API 行为保持不变，旧 seam 没被砍断

## 下一步
- 继续第三轮，优先专打剩余最重的几块：
  1. `数据采集模块`
  2. `语义 / 标签模块`
  3. `facts / 报告模块` 剩余 seam
