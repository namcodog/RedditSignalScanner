# Phase 310 - 第三轮 facts/报告模块下一刀：报告增强 workflow 收口

## 背景

第三轮继续啃 `facts / 报告模块` 的硬骨头。

上一刀已经把：

- 市场工作流
- 最终 payload builder

从 `ReportService` 里拆出去了。

但继续往里看，[report_service.py](/Users/hujia/Desktop/RedditSignalScanner/backend/app/services/report/report_service.py) 里还残留着一大段“分析结果增强工作流”：

- 竞品名称归一化
- 行动项兜底生成
- 证据不足标记
- 证据要点句摘要
- 机会标题 / slogan 补强
- 机会规模二次校准
- 审计落盘

大白话：

- `ReportService` 还在一边编排，一边自己亲手跑整条增强链

这不符合第三轮要继续推进的目标：

- 职责更单一
- 接口更稳
- 主服务继续变薄

---

## 这一步发现了什么？

### 1. `get_report()` 里还残留了一大坨增强逻辑

前面市场工作流、render bundle、payload builder 都已经拆出去了，但 `get_report()` 仍然自己背着：

- `normalization_rate`
- `normalizations_data`
- `action_items` 增强
- 机会规模乘子
- `llm-audit-{task_id}.json` 落盘

这会带来两个问题：

- 主服务继续过重
- 增强逻辑没有单一真相源

### 2. 审计落盘还存在一个隐蔽坏味道

旧实现里审计落盘那段代码还在“吃当前作用域变量”：

- `normalization_rate`
- `normalizations_data`
- 甚至 `metadata`

这类代码最大的问题不是马上炸，而是：

- 一改主链位置
- 就很容易悄悄失效
- 然后继续被 `try/except` 吞掉

大白话：

- 它之前更像“碰运气能写出来”
- 不像一条正式 workflow

---

## 是否需要修复？

需要，而且已经完成。

这次没有：

- 改数据库 schema
- 新增 migration
- 改报告业务内容口径

这次改的是：

- 报告增强 workflow 的边界
- 审计落盘的边界
- 对应测试门禁

---

## 精确修复方法

### 1. 新增独立增强 workflow

新增文件：

- `backend/app/services/report/report_enrichment_workflow.py`

正式收了：

- `ReportEnrichmentInput`
- `ReportEnrichmentResult`
- `build_report_enrichment_result(...)`
- `write_report_enrichment_audit(...)`

大白话：

- “报告增强怎么跑”
- “增强审计怎么写”

现在开始有自己的独立齿轮了。

### 2. 把 `ReportService.get_report()` 收成更薄的编排层

调整：

- `backend/app/services/report/report_service.py`

现在 `get_report()` 不再自己亲手背这条增强链，而是：

1. 先拿分析 payload  
2. 委托 `build_report_enrichment_result(...)`  
3. 继续走 render bundle / payload builder  
4. 最后委托 `write_report_enrichment_audit(...)`

这意味着：

- `ReportService` 继续往“编排壳”收
- 增强逻辑开始有正式边界

### 3. 用测试把新合同锁住

新增测试：

- `backend/tests/services/report/test_report_enrichment_workflow.py`

覆盖：

- 稀疏证据会被打上 `证据不足(n<2)` 标记
- 默认 `category/title` 会回到当前真实合同
- 审计 JSON 会稳定写出：
  - `task_id`
  - `llm_model`
  - `normalization_rate`
  - `details.normalizations`

同时保持报告链回归通过：

- `test_report_service.py`
- `test_market_workflow.py`
- `test_render_bundle.py`
- `test_report_payload_builder.py`

顺手一并修掉了这次重构里暴露出的一个真实断点：

- 我在瘦 `report_service.py` import 时把 `Path` 删早了
- 导致 controlled summary 那条 fallback 链在 `try` 里悄悄吃了 `NameError`
- 这次一起拉回来了

---

## 结果

### 结构结果

- 报告增强 workflow 开始有独立齿轮
- 审计落盘不再依赖主函数临时变量
- `ReportService` 继续变薄

### 工程结果

这一步把 `facts / 报告模块` 继续往下面这条准则推进了一层：

- 职责更清楚
- 统一接口协同
- 彼此少牵连
- 链路更顺、更可控

大白话：

- 现在不是主服务亲手“顺便把增强也做了”
- 而是增强链自己开始有了正式工作流

---

## 验证

### 1. 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_enrichment_workflow.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_market_workflow.py \
  tests/services/report/test_render_bundle.py \
  tests/services/report/test_report_payload_builder.py -q
```

结果：

- `20 passed`

### 2. 语法自检

```bash
python -m py_compile \
  backend/app/services/report/report_enrichment_workflow.py \
  backend/app/services/report/report_service.py \
  backend/tests/services/report/test_report_enrichment_workflow.py
```

结果：

- 通过

### 3. 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 这次执行的价值是什么？达到了什么目的？

这一步最值钱的地方，不是“多了一个 workflow 文件”，而是：

- 把 `ReportService` 里最容易继续缠回主链的增强逻辑先剪开了
- 把审计落盘从“最佳努力的临时变量拼装”收成了正式 helper
- 后面继续拆 `structured markdown / controlled html / audit` 这几层，会顺很多

一句大白话收口：

- 这刀把报告链里最容易继续长回去的一大坨增强逻辑先拆开了，第三轮节奏还是稳的，可以继续往 95 分以上推进。
