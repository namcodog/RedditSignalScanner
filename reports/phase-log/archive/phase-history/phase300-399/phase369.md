# Phase 369 - 报告模块 runtime/helper 大包收口

## 1. 发现了什么？

这次第三轮没有再碎跑，直接把报告模块剩下那一整包 runtime/helper 一口气收掉了。

真正的问题是：

- `backend/app/services/report/report_service.py`

虽然前面已经拆掉了：

- request workflow
- assembly workflow
- enrichment workflow
- controlled summary workflow
- inline structured workflow

但主服务里还留着一整组会继续拖重入口的 helper：

- analysis payload 校验
- member count 获取
- overview 构建
- report html 兜底格式化
- market mode / quality level 读取
- request deps 最终 wiring

同时，API 和测试里还有几处还在直接咬私有方法：

- `service._validate_analysis_payload(...)`
- `service._get_community_member_count(...)`
- `service._build_overview(...)`
- `ReportService._is_market_mode_enabled()`
- `svc._build_t1_market_report_md()`

大白话说：

- `ReportService` 之前已经不像大总管了
- 但它还没收成真正的“入口壳”
- API 和测试也还在咬旧私有口子，后面很容易继续漂

## 2. 是否需要修复？

需要，而且已经修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增统一 runtime 层

新增：

- `backend/app/services/report/report_runtime.py`

正式收了这一整组公共运行时能力：

- `resolve_report_quality_level()`
- `is_market_mode_enabled()`
- `ReportRuntime.validate_analysis_payload(...)`
- `ReportRuntime.fetch_community_member_count(...)`
- `ReportRuntime.build_overview(...)`
- `ReportRuntime.coerce_report_html(...)`
- `ReportRuntime.format_analysis_version(...)`
- `ReportRuntime.build_request_workflow_deps(...)`

也就是说：

- 现在报告模块这组 runtime/helper 开始只有一个正式真相源

### 3.2 收薄 ReportService

更新：

- `backend/app/services/report/report_service.py`

这次把主服务里原来那一整组 wrapper 基本都收掉了：

- `_get_quality_level`
- `_is_market_mode_enabled`
- `_report_request_workflow_deps`
- `_validate_analysis_payload`
- `_build_stats`
- `_get_community_member_count`
- `_build_overview`
- `_build_summary`
- `_build_market_health`
- `_build_metadata`
- `_coerce_report_html`
- `_format_analysis_version`

现在 `ReportService` 基本只保留：

- 配置/仓库/cache 初始化
- `get_report(...)`
- 少量对外 public 委托：
  - `validate_analysis_payload(...)`
  - `fetch_community_member_count(...)`
  - `build_overview(...)`
  - `coerce_report_html(...)`
  - `format_analysis_version(...)`

很直观的结果：

- `backend/app/services/report/report_service.py`
  - 现在是 `191` 行

### 3.3 API 和测试一起拉回当前真实合同

更新：

- `backend/app/api/v1/endpoints/reports.py`
- `backend/tests/services/report/test_report_service.py`
- `backend/tests/services/report/test_report_service_member_count.py`
- `backend/tests/services/report/test_report_service_market_switch.py`
- `backend/tests/services/report/test_report_service_t1_market_md.py`

这次统一做了两件事：

- 不再直接咬 `ReportService` 私有方法
- 测试和 API 都改成走当前 public 合同或独立 workflow

其中：

- market mode 开关测试，改成直接测 `report_runtime.is_market_mode_enabled()`
- market markdown 测试，改成直接测 `market_workflow.build_market_report_markdown(...)`

大白话说：

- 不再为了迁就旧测试，把主服务重新长回去

## 4. 测试与验证

### 第一轮定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_service_member_count.py \
  tests/services/report/test_report_request_deps_factory.py \
  tests/services/report/test_report_request_workflow.py -q
```

结果：

- `23 passed`

### 报告模块整组回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/report -q
```

结果：

- `105 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/report/report_runtime.py \
  backend/app/services/report/report_service.py \
  backend/app/api/v1/endpoints/reports.py \
  backend/tests/services/report/test_report_service_market_switch.py \
  backend/tests/services/report/test_report_service_t1_market_md.py
```

结果：

- 通过

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 5. 下一步系统性的计划是什么？

第三轮继续按“大包封板”推进，不再碎跑。

接下来优先顺序还是：

1. `数据采集模块` 最后一包
2. `语义 / 标签模块` 最后一包
3. 第三轮总复盘

当前完成度判断更新为：

- 第三轮完成度：约 `80%`
- 整个系统总完成度：约 `90%-91%`

也就是说：

- 报告模块这包现在基本已经封板
- 后面主要还剩采集和标签两组大包，以及最后总复盘

## 6. 这次执行的价值是什么？达到了什么目的？

这一步很值钱，因为：

- 报告模块这轮 runtime/helper 终于不再散在主服务里
- API 和测试也不再咬旧私有口子
- `ReportService` 终于更接近真正的入口壳

一句大白话：

- 这次不是再拆一个 seam，而是把报告模块剩下那整包会继续拖重主服务的 helper 和旧口子，一次性收紧了。
