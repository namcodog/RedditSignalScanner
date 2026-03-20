# Phase 286 - facts / 报告模块第一轮整治：分析真相源贯通到最终 ReportPayload

> 时间：2026-03-15  
> 模块：facts / 报告模块  
> 范围：`report_service`、`report_payload`、报告模块定向测试  
> 当前状态：已完成第一轮

---

## 1. 发现了什么？

这轮先没有去拆整个报告链，而是先盯最影响“整条链会不会说真话”的断点。

真正的问题是：

- 分析模块前一轮已经把很多真实状态写进了 `sources`
  - `report_tier`
  - `analysis_blocked`
  - `facts_v2_quality`
  - `structured_llm_status`
  - `structured_llm_reason`
  - `trend_source`
  - `trend_degraded`
  - `knowledge_graph`
  - `llm_used / llm_model / llm_rounds`
- 但报告层在 `_normalise_sources()` 里还按旧 allowlist 在裁剪字段
- 最终 `ReportPayload` 甚至没有 `sources` 字段

这会导致：

- 分析层已经开始说真话
- 报告层却把这些真相截掉
- 最终前端或下游只能看到“报告结果”，却看不到这次报告是被拦截、降级，还是结构化 LLM 失败

一句大白话：

- **以前分析层已经把原因说出来了，但报告层没有把这些原因带到最终输出。**

---

## 2. 是否需要修复？

需要，而且这轮已经修完第一刀。

这次没有改数据库 schema，也没有新增 migration。  
做的是三件事：

1. 把分析层新增的 `sources` 字段合同补进 schema
2. 把 `report_service` 的来源白名单对齐到当前真实合同
3. 把最终 `ReportPayload` 真正接上 `sources`

---

## 3. 精确修复方法？

### 3.1 `SourcesPayload` 跟上当前真实分析合同

修改：

- `backend/app/schemas/analysis.py`

新增字段：

- `report_tier`
- `analysis_blocked`
- `facts_v2_quality`
- `structured_llm_status`
- `structured_llm_reason`

这样“分析层真实会产出的字段”终于和 schema 对齐了，不再是：

- 代码里有
- schema 里没有

### 3.2 `_normalise_sources()` 白名单对齐真实来源字段

修改：

- `backend/app/services/report/report_service.py`

这轮把旧 allowlist 补齐到当前真实世界，新增保留：

- `report_tier`
- `analysis_blocked`
- `facts_v2_quality`
- `trend_source`
- `trend_degraded`
- `structured_llm_status`
- `structured_llm_reason`
- `knowledge_graph`
- `llm_used`
- `llm_model`
- `llm_rounds`

并补了对应默认值。

也就是说：

- **报告层不再把分析层已经说清楚的状态偷偷裁掉。**

### 3.3 最终 `ReportPayload` 正式接上 `sources`

修改：

- `backend/app/schemas/report_payload.py`
- `backend/app/services/report/report_service.py`

这轮新增：

- `ReportPayload.sources: SourcesPayload | None`

并在 `get_report(...)` 里真正写入：

- `sources=analysis_payload.sources`

这样最终对外的报告对象终于能带出：

- 这次报告是哪个 tier
- 是否被 quality gate 影响
- 结构化 LLM 是跳过、失败，还是成功
- 趋势数据是不是降级
- 本次报告用了哪个模型、几轮

一句话：

- **现在 facts / 报告层已经开始把分析层的真相原样带到最终 payload。**

### 3.4 测试门禁补齐

修改：

- `backend/tests/services/report/test_report_service_market_mode.py`

新增测试：

- `test_report_service_preserves_sources_contract_from_analysis`

它直接验证：

- 分析层写入的来源状态
- 能不能一路保留下来
- 最终通过 `payload.sources` 被拿到

这就不是文档约定了，而是：

- **代码接口 + 测试门禁一起把这套合同锁住了。**

---

## 4. 这轮结果是什么？

这轮的本质不是“报告更好看了”，而是：

- **分析层的真相源终于贯通到了最终报告输出。**

现在链路变成：

- 分析层说真话
- facts / 报告层不再截断
- 最终 payload 也能把状态和原因带出去

这更符合系统总整治的准则：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

---

## 5. 验证结果

### 报告模块定向测试

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_service_market_mode.py -q
```

结果：

- `6 passed`

### 报告模块回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_service_t1_market_md.py \
  tests/api/test_reports.py \
  tests/api/test_report_export_markdown_and_fallback.py \
  tests/api/test_reports_legacy_route_unit.py -q
```

结果：

- `27 passed, 1 skipped`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 6. 这轮还暴露了什么残留点？

这轮第一刀虽然已经把“真相源贯通”收住，但 facts / 报告模块还留着两个后续值得继续看的点：

1. 报告模块本体还是偏大  
   - `report_service.py` 仍然知道太多事
   - 第一轮先收真相源，不在这轮一口气拆大文件

2. 市场报告内容生成链仍然耦合较深  
   - 现在已经只剩一个最终输出口
   - 但内容装配、增强、渲染还在同一条大链里
   - 这更适合放到第二轮结构性收口里做

一句话：

- **这轮先把“报告层会截断分析真相”这个最伤可信度的问题收住了；下一轮如果继续做，重点会是结构降耦合，不是再补字段。**

---
