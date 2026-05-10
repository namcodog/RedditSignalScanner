# Phase 361 - report request deps 装配链抽离

## 1. 发现了什么？

这一步第三轮继续打的是 `facts / 报告模块` 里还偏重的一截：

- `backend/app/services/report/report_service.py`

虽然前面已经把：

- context loader
- assembly workflow
- enrichment workflow
- controlled summary workflow

都拆出去了，但 `ReportService._report_request_workflow_deps()` 还在自己维护一大段闭包装配：

- `load_report_request_context(...)`
- `assemble_report_payload(...)`
- `ReportAssemblyDeps(...)`
- cache / validate / membership / market mode 这些依赖 wiring

大白话说：

- 主服务虽然已经薄很多了
- 但“请求依赖怎么接起来”这件事还没有自己的独立齿轮

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增独立 deps factory

新增：

- `backend/app/services/report/report_request_deps_factory.py`

正式收了：

- `ReportRequestDepsFactoryInput`
- `build_report_request_workflow_deps(...)`

现在这块统一负责：

- request context loader 的 deps 装配
- report assembly workflow 的 deps 装配
- cache / validate / membership / market mode 这套 wiring

### 3.2 收薄 ReportService

更新：

- `backend/app/services/report/report_service.py`

现在 `ReportService._report_request_workflow_deps()` 不再自己维护一大段闭包和装配细节，而是变成薄委托：

1. 组装 `ReportRequestDepsFactoryInput`
2. 调 `build_report_request_workflow_deps(...)`
3. 返回 workflow deps

一个很直观的结果：

- `report_service.py` 现在是 `459` 行
- 新拆出的 `report_request_deps_factory.py` 是 `92` 行

也就是说：

- 主服务又薄了一层
- 请求装配链开始有自己的正式齿轮了

### 3.3 新增定向测试

新增：

- `backend/tests/services/report/test_report_request_deps_factory.py`

锁住两件事：

- load_context 这层确实委托到 `load_report_request_context(...)`
- assemble_payload 这层确实委托到 `assemble_report_payload(...)`

同时继续保留并跑通：

- `backend/tests/services/report/test_report_request_workflow.py`
- `backend/tests/services/report/test_report_service.py`

## 4. 测试与验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_request_deps_factory.py \
  tests/services/report/test_report_request_workflow.py \
  tests/services/report/test_report_service.py -q
```

结果：

- `16 passed`

### 语法自检

```bash
cd backend && python -m py_compile \
  app/services/report/report_request_deps_factory.py \
  app/services/report/report_service.py \
  tests/services/report/test_report_request_deps_factory.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方很直接：

- `ReportService` 里“请求依赖怎么接起来”这条装配链，开始有自己的独立齿轮了
- 后面再改：
  - cache
  - membership
  - request context
  - assembly deps
  就不容易再把主服务一起拖重

一句大白话：

- 这一步不是修小毛病，而是把报告模块里还留在主服务上的一大段请求装配链正式抽开了。
