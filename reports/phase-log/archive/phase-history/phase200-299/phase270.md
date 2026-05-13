# Phase 270 - Round 5 第三阶段：旧版报告路由收口

## 本轮目标

把 `backend/app/api/routes/reports.py` 从一份长期漂移的旧版复制实现，收成薄兼容层：

- 旧路径还在
- 行为不再自己维护两套
- 真正业务逻辑只认 `api/v1/endpoints/reports.py`

## 涉及文件

- `backend/app/api/routes/reports.py`
- `backend/tests/api/test_reports_legacy_route_unit.py`
- `reports/phase-log/phase270.md`
- `系统全量审计扫描计划.md`

## 发现了什么

- 旧版 `api/routes/reports.py` 之前仍保留一整份报告接口实现。
- 这会导致：
  - 第一阶段已经修好的真实社区导出/fallback 协议，旧文件还留着旧口径
  - 以后同一个报告接口改一次要改两份
  - 人和 AI 都更容易在旧文件上继续补新逻辑，造成再次漂移

## 是否需要修复

需要，而且这轮已经修完。

## 精确修复方法

### 1. 旧文件改成薄兼容层

`backend/app/api/routes/reports.py` 现在保留：

- legacy 路由定义
- 共享的 `REPORT_RATE_LIMITER`
- 共享的 `REPORT_CACHE`

其余 endpoint 行为统一改成：

- 惰性导入 `app.api.v1.endpoints.reports`
- 旧路由只做参数透传
- 真正逻辑全部交给 v1 实现

### 2. 防止继续漂移

新增单元测试 `backend/tests/api/test_reports_legacy_route_unit.py`，锁住：

- `get_analysis_report()` 会委托 v1
- `get_report_communities()` 会委托 v1 并保留响应头
- `export_communities()` 会委托 v1
- `download_report()` 会委托 v1

也就是说，后面谁要改报告口径，只改 v1 即可；旧路由不再自己藏分叉逻辑。

## 验证

### 旧路由委托测试

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/api/test_reports_legacy_route_unit.py -q
```

结果：

- `4 passed`

### 报告 API 回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/api/test_reports.py \
  tests/api/test_report_export_markdown_and_fallback.py \
  tests/api/test_reports_legacy_route_unit.py -q
```

结果：

- `20 passed, 1 skipped`

### 质量门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 结果

- `backend/app/api/routes/reports.py` 从历史大文件收成了兼容层
- 文件行数从约 `838` 行降到 `186` 行
- 新旧报告路由不再各自维护一套业务逻辑

## 统一口径

Round 5 第三阶段解决的是：

- 旧版报告路由继续复制业务逻辑，导致同一类接口存在两套真相

修完后统一口径变成：

- 报告 API 的真相实现只有一套：`api/v1/endpoints/reports.py`
- 旧路由只保留兼容入口，不再自己维护逻辑

## 下一步

Round 5 已全部完成。

后续可进入下一轮系统审计/修复，不需要再回头补 Round 5 收口。

## 价值

这轮的价值不是加功能，而是彻底封住“同一个报告接口两份代码各修各的”这个老口子。

一句大白话：

- 以后改报告接口，不用再担心新文件修好了，旧文件还在偷偷说旧话。
