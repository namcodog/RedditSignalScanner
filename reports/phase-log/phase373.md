# Phase 373 - 第三轮大包推进：报告模块 runtime / request-assembly 接线封板

## 1. 发现了什么？

这次不是继续拆一个小 seam，而是把报告模块里还分散着的 request / assembly 接线整包收掉了。

真正的问题是：

- `report_service.py` 已经很薄了
- 但 request deps 和 assembly deps 还分散在两套 factory 里
- `ReportRuntime`、request workflow、assembly workflow 三边还不是一个正式真相源

大白话说：

- 报告主服务已经不像大总管了
- 但“报告请求怎么把依赖接起来”这条线还没彻底封板

## 2. 是否需要修复？

需要，而且这一大包已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 收成统一 runtime 真相源

重建：

- `backend/app/services/report/report_runtime.py`

现在它正式承接：

- `build_report_assembly_deps(...)`
- `build_report_request_workflow_deps(...)`
- `resolve_report_quality_level(...)`
- `is_market_mode_enabled(...)`
- `fetch_community_member_count(...)`
- `build_overview(...)`
- `coerce_report_html(...)`
- `format_analysis_version(...)`

### 3.2 删除重复 factory

删除：

- `backend/app/services/report/report_request_deps_factory.py`
- `backend/app/services/report/report_assembly_deps_factory.py`

也就是说：

- request wiring 和 assembly wiring 不再各有一套外置 factory
- 统一由 `ReportRuntime` 这一层负责

### 3.3 测试回到当前真实合同

调整：

- `backend/tests/services/report/test_report_request_deps_factory.py`
- `backend/tests/services/report/test_report_assembly_deps_factory.py`

并确认：

- request workflow
- service 入口
- member count provider

都继续吃同一条 runtime 真相链。

## 4. 验证结果

### 4.1 定向回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_request_deps_factory.py \
  tests/services/report/test_report_assembly_deps_factory.py \
  tests/services/report/test_report_request_workflow.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_service_member_count.py -q
```

结果：

- `25 passed`

### 4.2 报告模块整组回归

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report -q
```

结果：

- `105 passed`

### 4.3 主门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.4 语法自检

命令：

```bash
python -m py_compile \
  backend/app/services/report/report_runtime.py \
  backend/app/services/report/report_service.py \
  backend/tests/services/report/test_report_request_deps_factory.py \
  backend/tests/services/report/test_report_assembly_deps_factory.py
```

结果：

- 通过

## 5. 文件体量变化

命令：

```bash
wc -l \
  backend/app/services/report/report_runtime.py \
  backend/app/services/report/report_service.py
```

结果：

- `report_runtime.py`: `435`
- `report_service.py`: `191`

最关键的不是单个文件大小，而是：

- request wiring
- assembly wiring
- service 入口

现在终于开始站在同一条真相链上。

## 6. 当前完成度判断

这一步之后，我的判断是：

- 第三轮完成度：约 `90%-91%`
- 系统整体完成度：约 `94%-95%`

离 `95+` 还差最后几包：

1. 数据采集模块剩余 wrapper / runtime wiring 清尾
2. 语义 / 标签模块剩余 sync / import-export 接缝清尾
3. 第三轮总复盘和最终封板判断

## 7. 这次执行的价值是什么？达到了什么目的？

这次最值钱的地方很直接：

- 报告模块里“请求怎么接线、装配怎么接线”现在只有一个正式真相源了
- `ReportService` 保持薄入口
- 后面再改 market wiring、controlled summary、structured report、audit，不容易把主服务重新拖回去

一句大白话总结：

- 这次把报告模块最后一大包 request / assembly 接线真正封板了。
