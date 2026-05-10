# Phase 363 - report assembly deps 装配链抽离

## 1. 发现了什么？

这一步第三轮继续打的是 `facts / 报告模块` 里还留在主服务上的另一截装配链：

- `backend/app/services/report/report_service.py`

虽然前面已经把：

- request deps factory
- request context loader
- assembly workflow
- enrichment workflow
- controlled summary workflow

都拆出去了，但 `ReportService._report_request_workflow_deps()` 里还在自己手工接一大段 `ReportAssemblyDeps(...)`：

- market markdown
- market enhancements
- controlled markdown
- inline structured report
- structured markdown
- enrichment audit

大白话说：

- 主服务虽然已经很薄了
- 但“报告装配依赖怎么接起来”这件事还没有自己的正式齿轮

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 assembly deps factory

新增：

- `backend/app/services/report/report_assembly_deps_factory.py`

正式收了：

- `ReportAssemblyDepsFactoryInput`
- `build_report_assembly_deps(...)`

现在这块统一负责：

- market markdown wiring
- market enhancements wiring
- controlled markdown wiring
- inline structured report wiring
- structured markdown wiring
- enrichment audit wiring

### 3.2 收薄 request deps factory 和 ReportService

更新：

- `backend/app/services/report/report_request_deps_factory.py`
- `backend/app/services/report/report_service.py`

现在：

- `ReportRequestDepsFactoryInput` 不再背一大串零散 callable
- 改成只接：
  - `assembly_deps`
  - `prefer_market_report`

`ReportService._report_request_workflow_deps()` 也不再自己维护那段 `ReportAssemblyDeps(...)` 装配，而是变成薄委托：

1. 组装 `ReportAssemblyDepsFactoryInput`
2. 调 `build_report_assembly_deps(...)`
3. 把结果塞进 `ReportRequestDepsFactoryInput`
4. 再调 `build_report_request_workflow_deps(...)`

也就是说：

- 主服务又薄了一层
- request deps factory 也更像真正的 request-level wiring
- assembly wiring 开始有自己的正式真相源了

### 3.3 修正定向测试到当前真实合同

更新：

- `backend/tests/services/report/test_report_request_deps_factory.py`

这两条测试之前还按旧世界构造 `ReportRequestDepsFactoryInput(...)`，继续传：

- `maybe_generate_structured_report`
- `build_market_enhancements`
- `build_controlled_report_markdown`
- `render_structured_markdown`
- `coerce_report_html`
- `fetch_member_count`
- `write_enrichment_audit`

现在已经收成当前真实合同：

- 显式传 `assembly_deps`
- 断言 `assemble_report_payload(...)` 确实吃到这份 `assembly_deps`
- 断言 `prefer_market_report` 仍然稳定透传

## 4. 测试与验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_assembly_deps_factory.py \
  tests/services/report/test_report_request_deps_factory.py \
  tests/services/report/test_report_request_workflow.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_assembly_workflow.py \
  tests/services/report/test_inline_structured_report_workflow.py -q
```

结果：

- `24 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `ReportService` 里“报告装配依赖怎么接起来”这条链，现在也开始有自己的独立齿轮了
- 后面再改：
  - market wiring
  - controlled markdown wiring
  - structured report wiring
  - enrichment audit wiring
  就不容易再把主服务和 request factory 一起拖重

一句大白话：

- 这一步不是修小毛病，而是把报告模块里还留在主服务上的 assembly wiring 正式抽开了。
