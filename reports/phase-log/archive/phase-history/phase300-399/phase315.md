# Phase 315 - 第三轮继续打磨：analysis payload loader 拆分收口

## 1. 发现了什么？

- `ReportService` 里还残留了一整套分析 payload 的迁移、规范化、版本处理和校验逻辑。
- 这条链虽然已经能跑，但主服务还在自己背：
  - `0.9 -> 1.0` 迁移
  - `insights` 规范化
  - `sources` 白名单清洗
  - `analysis_version` 格式化
  - `AnalysisRead` 校验
- 大白话说：
  - 报告主服务还在一边编排，一边自己处理分析 payload 的“脏活”。

## 2. 是否需要修复？

- 需要，而且已经修完。
- 这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增独立 loader 层

新增：

- `backend/app/services/report/analysis_payload_loader.py`

正式收了：

- `AnalysisPayloadValidationError`
- `classify_severity(...)`
- `format_analysis_version(...)`
- `validate_report_analysis_payload(...)`

以及内部迁移/规范化 helper：

- `_normalise_insights(...)`
- `_normalise_sources(...)`
- `_migrate_v09_to_v10(...)`
- `_apply_version_migrations(...)`

### 3.2 收薄 ReportService

修改：

- `backend/app/services/report/report_service.py`

现在：

- `_validate_analysis_payload(...)` 改成委托 `validate_report_analysis_payload(...)`
- `_format_analysis_version(...)` 改成委托 `format_analysis_version(...)`
- 主服务不再自己维护那一大坨 payload migration / normalization 细节

同时补回了仍被兼容 wrapper 用到的 builder import，避免旧 wrapper seam 出现 `NameError`。

### 3.3 先补测试，再锁合同

新增：

- `backend/tests/services/report/test_analysis_payload_loader.py`

并把新测试样本补到当前真实 schema 要求：

- `pain_points.frequency`
- `opportunities.relevance_score`
- `opportunities.potential_users`

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_analysis_payload_loader.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_assembly_workflow.py \
  tests/services/report/test_report_payload_builder.py \
  tests/services/report/test_report_enrichment_workflow.py \
  tests/services/report/test_controlled_summary_workflow.py \
  tests/services/report/test_report_service_member_count.py -q
```

结果：

- `36 passed`

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/report/analysis_payload_loader.py \
  backend/app/services/report/report_service.py \
  backend/tests/services/report/test_analysis_payload_loader.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

- 报告链里“分析 payload 怎么迁移、怎么洗干净、怎么校验”现在开始有自己的独立齿轮了。
- `ReportService` 更像真正的编排层，不再继续背这坨脏活。
- 这一步继续把第三轮往 `95+` 的目标推进：
  - 职责更单一
  - 接口更稳
  - 主服务更薄
  - 兼容 seam 还在，但不再反过来绑死主逻辑

一句大白话：

- **这刀把报告链里那块“主服务亲手洗 payload”的重逻辑拆开了，第三轮又顺了一层。**
