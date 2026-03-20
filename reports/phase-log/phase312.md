# Phase 312 - 第三轮 facts/报告模块下一刀：controlled summary workflow 收口

## 背景

第三轮继续打 `facts / 报告模块` 里剩余最重的耦合点。

前几刀已经把：

- `market_workflow`
- `render_bundle`
- `report_payload_builder`
- `report_enrichment_workflow`

这些块从 [report_service.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/report/report_service.py) 里拆出去了。

但继续往里看，`ReportService` 里还残留着一坨不该继续留在编排层的逻辑：

- `controlled summary` 的文件路径兜底
- lexicon / metrics / template 读取
- controlled generator 上下文构建
- markdown 渲染

大白话：

- `ReportService` 还在一边编排，一边自己摸文件系统、拼渲染上下文

这不符合第三轮继续推进的目标：

- 主服务更薄
- workflow 更独立
- 边界更清楚

---

## 这一步发现了什么？

### 1. `_render_controlled_summary_markdown()` 还是一坨混合逻辑

这个方法之前同时背着：

- 环境变量读取
- 路径候选解析
- 文件存在判断
- JSON 读取
- controlled generator 调用

也就是说：

- 编排层还在自己做“资源发现 + 读取 + 渲染”

### 2. 这块不拆，`ReportService` 很容易继续长回去

报告链现在已经开始像编排层了，但 controlled summary 这块如果继续留着：

- 每次改模板路径
- 改 metrics 来源
- 改 lexicon/fallback

都还得回主服务里动刀。

### 3. 这块是个很好的 seam

它业务风险不高，但结构收益很值：

- 输入清楚：`analysis_payload / task_id / blocked flag`
- 输出清楚：`markdown / metrics_data`
- 不动最终 payload 合同
- 不动对外报告口径

大白话：

- 这是一刀典型的“爆炸半径小、收益大”的 seam

---

## 是否需要修复？

需要，而且已经完成。

这次没有：

- 改数据库 schema
- 新增 migration
- 改对外报告合同

这次改的是：

- controlled summary 的 workflow 边界
- `ReportService` 的内部职责
- 对应测试门禁

---

## 精确修复方法

### 1. 新增独立 workflow

新增文件：

- `backend/app/services/report/controlled_summary_workflow.py`

正式收了：

- `ControlledSummaryWorkflowDeps`
- `ControlledSummaryWorkflowResult`
- `render_controlled_summary_workflow(...)`

这块现在正式承接：

- 路径候选解析
- lexicon / metrics / template 读取
- controlled generator ctx / render

### 2. 把 `ReportService` 收成薄委托

调整：

- `backend/app/services/report/report_service.py`

现在 `_render_controlled_summary_markdown()` 不再自己手工做整条链，而是：

1. 组装 deps
2. 调 `render_controlled_summary_workflow(...)`
3. 返回 tuple

也就是说：

- `ReportService` 继续往“编排壳”收
- controlled summary 开始有自己的独立齿轮

### 3. 先补 workflow 测试，再锁旧链兼容

新增：

- `backend/tests/services/report/test_controlled_summary_workflow.py`

覆盖了：

- 文件存在时能正确渲染
- 被质量门拦截时短路
- template 缺失时稳定返回空结果

同时保持原有报告链回归通过：

- `test_market_workflow.py`
- `test_render_bundle.py`
- `test_report_service.py`
- `test_report_payload_builder.py`
- `test_report_enrichment_workflow.py`

---

## 结果

### 结构结果

- controlled summary workflow 开始有独立齿轮
- `ReportService` 继续变薄
- 文件系统读取和渲染上下文不再继续缠在主服务里

### 工程结果

一个很直观的结果：

- `backend/app/services/report/report_service.py`
  - 从上一刀后的 `1148` 行
  - 降到了现在的 `1089` 行

### 为什么这一步值钱

这一步真正推进的是：

- 主服务更像编排层
- 渲染相关资源加载有正式边界
- 后面继续拆报告链，不用再回主服务里摸文件路径和 fallback 细节

一句大白话：

- 报告链里“编排”和“摸文件 + 渲染”现在开始各回各位了

---

## 验证

### 1. 语法自检

```bash
python -m py_compile \
  backend/app/services/report/controlled_summary_workflow.py \
  backend/app/services/report/report_service.py \
  backend/tests/services/report/test_controlled_summary_workflow.py
```

结果：

- 通过

### 2. 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_controlled_summary_workflow.py \
  tests/services/report/test_market_workflow.py \
  tests/services/report/test_render_bundle.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_payload_builder.py \
  tests/services/report/test_report_enrichment_workflow.py -q
```

结果：

- `23 passed`

### 3. 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 下一步

按第三轮现在的节奏，下一刀继续专打剩余最重的耦合点。

当前优先建议回到：

1. `语义 / 标签模块`
2. 或 `数据采集模块`

继续沿同一条准则推进：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

一句大白话收口：

- 这刀把报告链里最后一块还在“主服务亲手摸文件系统”的重逻辑拆开了，第三轮节奏还是稳的，可以继续往 95 分以上推进。
