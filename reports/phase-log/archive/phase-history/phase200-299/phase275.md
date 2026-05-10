# Phase 275 - 报告输出口统一 + 对外命名收口

## 背景

用户指出两个根问题：

1. 报告链里还留着“新旧两套入口/两段生成逻辑”，不符合“只维护一个真输出口”的原则。
2. `T1 market` 属于后端内部社区分层黑话，不应该继续漏到用户看到的报告标题里。

本轮目标不是再补兼容壳，而是把报告输出重新收成：

- 内部兼容符号可以先留
- 对外文案统一改成人能看懂的话
- `ReportService` 内部只保留一条受控 markdown 输出决策链

## 发现

- `report_service.py` 里之前同时保留了两段 markdown 生成逻辑：
  - Controlled Executive Summary v2
  - market insight markdown，再覆盖前者
- 这种写法导致：
  - 行数膨胀
  - 分支重复
  - “单一输出口”没有真正落地
- 此外，`market_enhancements` 是既有合同，不是废逻辑：
  - `personas`
  - `quotes`
  - `saturation`
  - `gtm_plans`
  这些都还被现有 Phase 1 / Phase 2 测试依赖，不能在收口时顺手删掉。

## 修复

### 1. 报告输出口收成一条链

在 `backend/app/services/report/report_service.py` 中新增了两个 helper：

- `_render_controlled_summary_markdown(...)`
- `_build_controlled_report_markdown(...)`

现在 `get_report()` 不再自己拼两大段 markdown 逻辑，而是统一通过 `_build_controlled_report_markdown(...)` 决定：

- 优先走社区市场洞察 markdown
- 不可用时退回 controlled executive summary

也就是说：

- 最终 HTML 仍然只从一个 `controlled_md` 变量往下走
- 决策点被收口成一个 helper
- `get_report()` 里不再同时维护两套大分支

### 2. 对外去掉 `T1 market` 黑话

对外用户可见标题统一改成：

- `社区市场洞察报告`

已修改：

- `backend/app/services/report/t1_market_agent.py`
- `backend/app/services/report/market_report.py`

说明：

- `T1MarketReportAgent` 这个类名暂时保留，只作为内部兼容符号
- 用户看到的正文标题、模板标题、`market_enhancements.mode` 已统一改成更清楚的表达：
  - `社区市场洞察报告`
  - `community_market`

### 3. 保住既有增强合同

`market_enhancements` 现在继续稳定输出：

- `mode`
- `personas`
- `quotes`
- `saturation`
- `gtm_plans`

同时修了两个深层问题：

- `gtm_plans` 在测试桩返回 dict persona 时会炸，现在会自动退回 quick personas
- `_serialize_market_value()` 改成递归序列化，避免 `GTMPlan` dataclass 混进返回 payload

## 影响文件

- `backend/app/services/report/report_service.py`
- `backend/app/services/report/t1_market_agent.py`
- `backend/app/services/report/market_report.py`
- `backend/tests/services/report/test_market_report_builder.py`

## 验证

### 定向报告链回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_t1_market_agent.py \
  tests/services/analysis/test_t1_market_agent_llm.py \
  tests/services/report/test_report_service_t1_market_md.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_service_phase1_integration.py \
  tests/services/report/test_report_service_phase2_integration.py \
  tests/services/report/test_report_service_phase2_e2e_stub.py \
  tests/services/report/test_market_report_builder.py -q
```

结果：`14 passed`

### 报告 API / 旧路由回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/api/test_reports.py \
  tests/api/test_report_export_markdown_and_fallback.py \
  tests/api/test_reports_legacy_route_unit.py -q
```

结果：`20 passed, 1 skipped`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：`27 passed`

## 最终口径

这轮之后，报告链的统一口径是：

- 报告只保留一个受控输出口
- 对外不再暴露 `T1 market` 这种内部黑话
- 内部兼容符号可以暂留，但不能继续污染用户看到的内容
- 增强数据继续保留，但只通过统一的 `community_market` 口径对外表达
