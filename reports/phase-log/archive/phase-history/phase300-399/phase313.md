# Phase 313 - 第三轮继续打磨：报告总装配 workflow 拆分

## 1. 这次发现了什么

- `ReportService.get_report()` 还在同时背完整报告装配链：
  - facts_v2 质量门判断
  - inline structured LLM 生成
  - enrichment workflow
  - controlled markdown fallback
  - render bundle 组装
  - 最终 payload 生成
  - audit 落盘
- 也就是说，`ReportService` 还在一边做编排，一边亲手跑完整 workflow。
- 这已经不符合第三轮现在的目标：
  - 主服务继续变薄
  - workflow 继续独立成齿轮
  - 单一真相源继续做硬

## 2. 是否需要修复

- 需要。
- 这次没有改数据库表结构，没有新 migration。
- 改的是 `facts / 报告模块` 的总装配边界、测试门禁和 phase 记录。

## 3. 精确修复方法

### 3.1 新增独立装配 workflow

新增文件：

- `backend/app/services/report/report_assembly_workflow.py`

新增正式合同：

- `ReportAssemblyInput`
- `ReportAssemblyDeps`
- `ReportAssemblyResult`
- `assemble_report_payload(...)`

这条 workflow 现在统一承接：

- quality gate blocked 判断
- inline structured report 尝试生成
- enrichment 结果生成
- controlled markdown fallback 判定
- render bundle 组装
- final payload 生成
- audit 写入（最佳努力）

### 3.2 收薄 ReportService

修改文件：

- `backend/app/services/report/report_service.py`

变化：

- `get_report()` 不再自己手搓整条装配链
- 现在只负责：
  - 取 task / analysis
  - 做权限校验
  - 做 cache 命中判断
  - 调 `assemble_report_payload(...)`
  - 写 cache 并返回 payload

另外新增：

- `_build_inline_structured_report(...)`
- `_write_report_enrichment_audit(...)`

让 service 侧只保留轻量委托 seam，不再把整条 workflow 塞在主函数里。

### 3.3 先补 workflow 测试，再锁旧链兼容

新增测试：

- `backend/tests/services/report/test_report_assembly_workflow.py`

覆盖：

- 有基础 HTML 时：
  - workflow 会生成 structured report
  - 不会误走 controlled fallback
  - 会触发 audit
- 被 quality gate 拦截且无基础 HTML 时：
  - workflow 会正确判定 blocked
  - 会走 controlled fallback
  - 会把 blocked 状态传给下游

旧链兼容测试继续通过：

- `backend/tests/services/report/test_report_service.py`
- `backend/tests/services/report/test_market_workflow.py`
- `backend/tests/services/report/test_render_bundle.py`
- `backend/tests/services/report/test_report_payload_builder.py`
- `backend/tests/services/report/test_report_enrichment_workflow.py`
- `backend/tests/services/report/test_controlled_summary_workflow.py`

## 4. 结果

- `ReportService` 继续变薄：
  - `backend/app/services/report/report_service.py`
  - 当前行数：`1059`
- 新装配 workflow 独立成单独齿轮：
  - `backend/app/services/report/report_assembly_workflow.py`
  - 当前行数：`161`

## 5. 验证

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_assembly_workflow.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_market_workflow.py \
  tests/services/report/test_render_bundle.py \
  tests/services/report/test_report_payload_builder.py \
  tests/services/report/test_report_enrichment_workflow.py \
  tests/services/report/test_controlled_summary_workflow.py -q
```

结果：

- `25 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/report/report_assembly_workflow.py \
  backend/app/services/report/report_service.py \
  backend/tests/services/report/test_report_assembly_workflow.py
```

结果：

- 通过

## 6. 这次执行的价值

- 报告链里“完整报告怎么装出来”现在开始有自己的独立 workflow 了。
- `ReportService` 更像真正的编排层，不再继续做一边调度、一边亲手跑整条装配链的“大总管”。
- 这一步继续朝当前总整治目标推进：
  - 各模块职责清楚
  - 通过统一接口协同
  - 彼此少牵连
  - 整条链路顺畅可控

## 7. 下一步建议

- 优先继续打 `facts / 报告模块` 和 `语义 / 标签模块` 剩余最重的耦合点。
- 原则不变：
  - 专打“主服务既编排又亲手干重活”的地方
  - 继续把单一真相源做硬
  - 继续朝 `95+` 的本地产品级稳定状态推进
