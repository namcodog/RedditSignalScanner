# Phase 377 - 第三轮大包推进：report_runtime helper 与 wiring 成组收口

## 1. 发现了什么？

这次收的不是 `ReportService`，而是它背后的 `report_runtime` 整包。

之前主服务已经很薄了，但 `backend/app/services/report/report_runtime.py` 还自己背着两大组重逻辑：

- runtime helper：
  - quality level
  - market mode
  - analysis payload 校验
  - community member count
  - overview
  - html coercion
  - analysis version 格式化
- runtime wiring：
  - assembly deps 装配
  - request workflow deps 装配

大白话说：

- `ReportService` 已经像入口了
- 但 `report_runtime` 还像一个大总管

## 2. 是否需要修复？

需要，而且这一整包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 helper 模块

新增：

- `backend/app/services/report/report_runtime_helpers.py`

正式收了：

- `resolve_report_quality_level(...)`
- `is_market_mode_enabled(...)`
- `validate_runtime_analysis_payload(...)`
- `fetch_runtime_community_member_count(...)`
- `build_runtime_overview(...)`
- `coerce_runtime_report_html(...)`
- `format_runtime_analysis_version(...)`

### 3.2 新增 factory 模块

新增：

- `backend/app/services/report/report_runtime_factory.py`

正式收了：

- `ReportAssemblyDepsFactoryInput`
- `ReportRequestDepsFactoryInput`
- `build_report_assembly_deps(...)`
- `build_report_request_workflow_deps(...)`
- `default_membership_allowed(...)`

### 3.3 收薄 report_runtime

调整：

- `backend/app/services/report/report_runtime.py`

现在这个文件主要只保留：

- `ReportRuntime` 这个 runtime 壳
- 对 helper / factory 的薄委托
- 兼容现有测试 patch seam 的导出边界

一个很直观的结果：

- `report_runtime.py` 从 `435` 行，压到了现在的 `165` 行

当前文件体量：

- `report_runtime.py`: `165`
- `report_runtime_factory.py`: `247`
- `report_runtime_helpers.py`: `126`

## 4. 补平的兼容问题

这次大包推进里，顺手补平了 3 类兼容口子：

1. `settings` 在拆分后被漏掉，导致 runtime 读配置时报 `NameError`
2. `format_runtime_analysis_version(None)` 需要继续保持返回 `unknown`
3. 老测试还在 patch `report_runtime` 的旧 seam
   所以对应的 patch 点统一改成当前真实边界：
   - `report_runtime_factory`

也就是说：

- 没有回头推翻这次大包方向
- 只是把旧 seam 拉回了当前真实世界

## 5. 验证结果

### 5.1 报告模块成组回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_runtime_helpers.py \
  tests/services/report/test_report_assembly_deps_factory.py \
  tests/services/report/test_report_request_deps_factory.py \
  tests/services/report/test_report_request_workflow.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_service_market_template_config.py \
  tests/services/report/test_report_service_member_count.py -q
```

结果：

- `36 passed`

### 5.2 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 5.3 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/report/report_runtime.py \
  backend/app/services/report/report_runtime_factory.py \
  backend/app/services/report/report_runtime_helpers.py \
  backend/tests/services/report/test_report_runtime_helpers.py
```

结果：

- 通过

## 6. 当前完成度判断

这一步之后，我的判断是：

- 第三轮完成度：约 `92%-93%`
- 系统整体完成度：约 `95%-96%`

剩下还要打的，已经不多了，主要是：

1. 数据采集模块最后一包清尾
2. 语义 / 标签模块最后一包清尾
3. 第三轮总复盘，判断是否正式站稳 `95+`

## 7. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `ReportService` 后面那层 runtime 现在也不再是一个大总管了
- helper 和 wiring 都开始有各自正式真相源
- 后面再改：
  - market mode
  - request context
  - assembly deps
  - validation / overview / member count
  不容易再把 runtime 壳一起拖重

一句大白话总结：

- 这次把报告模块剩下最重的一整包真正抽开了，第三轮已经很接近最后封板阶段。
