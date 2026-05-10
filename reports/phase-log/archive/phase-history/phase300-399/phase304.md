# Phase 304 - 第三轮第二刀：facts/报告模块市场工作流独立

> 时间：2026-03-15
> 模块：facts / 报告模块
> 范围：`report_service`、community market 工作流、受控 markdown 决策链
> 当前状态：已完成第三轮第二刀

---

## 1. 发现了什么？

第三轮进入 facts / 报告模块后，这一刀继续盯 `ReportService` 里最重、最容易缠回去的那块：

1. **community market 工作流还挂在主服务里**
   - `T1/社区市场洞察 markdown` 生成
   - `market_enhancements` 组装
   - controlled markdown 选择逻辑
   - 这些都还在 `report_service.py` 里直接编排

2. **主服务一边当编排层，一边继续背市场工作流细节**
   - 查 stats
   - 查 pain clusters
   - 调 agent
   - 拼 fallback
   - 再决定最终 controlled markdown

一句大白话：

- **第二轮先把受控渲染组装层拆开了，第三轮这一刀继续把“社区市场洞察工作流”从主服务里拆出去。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这轮做的是结构性拆分，不是报告内容降级。

---

## 3. 精确修复方法？

### 3.1 新增独立市场工作流层

新增：

- `backend/app/services/report/market_workflow.py`

把原来散在 `ReportService` 里的市场工作流职责收进去：

- `serialize_market_value(...)`
- `build_market_report_markdown(...)`
- `build_market_enhancements(...)`
- `build_controlled_markdown_result(...)`

这样现在不再是：

- `ReportService` 既查数、又调 agent、又拼 controlled markdown

而是：

- 主服务交给独立 workflow 层去完成这块市场工作流

### 3.2 `ReportService` 收成更薄的兼容入口

修改：

- `backend/app/services/report/report_service.py`

把这三个旧方法收成轻量委托：

- `_build_t1_market_report_md(...)`
- `_build_market_enhancements(...)`
- `_build_controlled_report_markdown(...)`

它们现在仍然保留同名入口，但内部只是转发到：

- `market_workflow.py`

这样做的目的不是“继续保留双份逻辑”，而是：

- **先把主服务瘦下来**
- **同时保住现有调用点和测试 seam**

一句大白话：

- **先拆真耦合，再慢慢退兼容壳。**

### 3.3 测试跟着新边界走，不再绑死旧模块路径

新增：

- `backend/tests/services/report/test_market_workflow.py`

并调整：

- `backend/tests/services/report/test_report_service_t1_market_md.py`

把原来 monkeypatch 在 `report_service` 里的：

- `build_stats_snapshot`
- `build_pain_clusters`

改到新的真实边界：

- `app.services.report.market_workflow.build_stats_snapshot`
- `app.services.report.market_workflow.build_pain_clusters`

这一步很重要，因为它让测试开始锁住“现在真实的齿轮边界”，而不是继续拖着旧世界跑。

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“报告更花”，而是：

- `ReportService` 继续从大总管往真正编排层收
- community market 这块开始有自己的正式工作流边界
- 后面再继续拆 facts 整理、输出壳、兼容层，会顺很多

一句大白话：

- **这刀把报告链里最容易继续缠回主服务的“市场工作流”先抽成独立齿轮了。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_market_workflow.py \
  tests/services/report/test_report_service_t1_market_md.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_service_phase1_integration.py \
  tests/services/report/test_report_service_phase2_integration.py \
  tests/services/report/test_render_bundle.py \
  tests/services/report/test_report_service.py -q
```

结果：

- `27 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/report/report_service.py \
  backend/app/services/report/market_workflow.py \
  backend/tests/services/report/test_market_workflow.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

facts / 报告模块第三轮这一刀之后，主服务仍然还有几块继续偏重：

1. `ReportService` 仍然整体偏大
2. facts 整理和最终 payload 输出壳，还能继续拆
3. 兼容入口还在，但已经开始变薄

所以这轮的正确定位是：

- **第三轮第二刀已经把社区市场洞察工作流拆出来了**
- 但不是 facts / 报告模块第三轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第三轮既定节奏，下一步进入：

- **数据采集模块** 的第三轮打磨

重点继续沿着同一条线：

- 继续压薄 `crawler_task / crawl_execute_task`
- 继续把调度、执行、写入、副作用拆回各自边界
- 继续把最重的齿轮打磨顺

一句话：

- **这刀先把报告链里最重的一块市场工作流拆开，下一步回到上游继续打磨采集链。**
