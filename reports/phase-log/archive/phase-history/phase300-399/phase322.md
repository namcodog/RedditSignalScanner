# Phase 322 - 第三轮：报告模块继续压薄 structured markdown 渲染层

## 1. 发现了什么？

- `ReportService` 里还残留一块很重的纯渲染逻辑：`_render_structured_markdown()`。
- 这块逻辑本身不需要数据库、不需要主服务状态，却一直挂在主服务里，继续放大会让：
  - 主服务继续偏胖
  - 渲染合同继续靠内部静态方法维持
  - 后面 AI 和人继续把“报告编排”和“结构化 markdown 渲染”混成一层

大白话：

- `ReportService` 还在亲手写“结构化市场洞察报告”的整段 markdown。

## 2. 是否需要修复？

- 需要。
- 这是第三轮很典型的一刀：
  - 不是补状态
  - 不是修表面 bug
  - 而是继续把主服务里“亲手干重活”的部分拆成独立齿轮

## 3. 精确修复方法？

### 3.1 新增独立 renderer

- 新增文件：
  - `backend/app/services/report/structured_report_renderer.py`
- 正式收口：
  - `render_structured_report_markdown(...)`

职责固定为：

- 接收 `report_structured`
- 读取 `facts_slice`
- 读取 `pain_points`
- 生成结构化 markdown

它不再依赖 `ReportService` 内部状态。

### 3.2 ReportService 改成薄委托

- 修改：
  - `backend/app/services/report/report_service.py`

现在 `get_report()` 通过 `render_structured_report_markdown(...)` 渲染结构化 markdown，不再依赖主服务内部的 `_render_structured_markdown()` 大段实现。

### 3.3 补测试锁合同

- 新增：
  - `backend/tests/services/report/test_structured_report_renderer.py`

覆盖：

- 空 payload 时返回 `None`
- 正常结构化 payload 时能稳定输出关键章节：
  - 顶部信息
  - 决策卡片
  - 核心战场
  - 用户痛点
  - 商业机会

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_structured_report_renderer.py \
  tests/services/report/test_report_assembly_workflow.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_context_loader.py \
  tests/services/report/test_analysis_payload_loader.py \
  tests/services/report/test_report_enrichment_workflow.py \
  tests/services/report/test_controlled_summary_workflow.py \
  tests/services/report/test_report_payload_builder.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_service_member_count.py -q
```

结果：

- `41 passed`

### 语法检查

```bash
python -m py_compile \
  backend/app/services/report/report_service.py \
  backend/app/services/report/structured_report_renderer.py \
  backend/tests/services/report/test_structured_report_renderer.py
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

这刀最值钱的地方很直接：

- `ReportService` 继续变薄
- 结构化 markdown 渲染开始有自己的独立真相源
- 报告链继续从“大总管式主服务”往“编排层 + 独立齿轮”推进

当前直观结果：

- `backend/app/services/report/report_service.py`：`494` 行
- `backend/app/services/report/structured_report_renderer.py`：`271` 行

一句大白话总结：

- 第三轮这一步，把报告链里还挂在主服务上的一大段纯渲染逻辑拆开了，系统又顺了一层。
