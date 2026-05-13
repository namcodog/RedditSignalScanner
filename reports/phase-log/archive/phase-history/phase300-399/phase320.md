# Phase 320 - 第三轮继续打磨：报告上下文加载链拆分

## 1. 发现了什么？

- `ReportService.get_report()` 里还残留着一条前置门禁重链：
  - 查 task + analysis
  - 任务归属校验
  - task 完成状态校验
  - analysis / report 存在性校验
  - 会员层级校验
  - cache key 组织
- 大白话说：
  - **主服务还在一进来就自己兼任门卫、验票员和上下文装配工。**

## 2. 是否需要修复？

- 需要，而且已经修完。
- 这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增独立 context loader

新增：

- `backend/app/services/report/report_context_loader.py`

正式收了：

- `ReportRequestContext`
- `ReportContextLoaderDeps`
- `load_report_request_context(...)`

把原来缠在 `get_report()` 前半段的这些动作收回到独立 loader：

- task / analysis 读取
- 用户归属校验
- task 已完成校验
- analysis / report 存在性校验
- 会员层级校验
- cache key 生成

### 3.2 收薄 ReportService.get_report

修改：

- `backend/app/services/report/report_service.py`

现在：

- `get_report()` 不再自己手写整段 access/context 链
- 改成先调用 `load_report_request_context(...)`
- 然后才进入 cache 判断、analysis payload 校验和后续 assembly workflow

也就是：

- **ReportService 更像编排层**
- **前置门禁开始有自己的独立齿轮**

### 3.3 测试门禁

新增：

- `backend/tests/services/report/test_report_context_loader.py`

覆盖：

- 正常返回 `task / analysis / cache_key`
- 会员层级不够时会拒绝
- report 缺失时会拒绝

同时保留：

- `backend/tests/services/report/test_report_service.py`
- 以及整组报告链定向回归

锁住：

- 新 loader 没把现有报告链带歪
- cache 命中不重新触发 payload 验证这条旧合同保持成立

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/report/test_report_context_loader.py \
  tests/services/report/test_report_service.py \
  tests/services/report/test_report_assembly_workflow.py \
  tests/services/report/test_analysis_payload_loader.py \
  tests/services/report/test_report_enrichment_workflow.py \
  tests/services/report/test_controlled_summary_workflow.py \
  tests/services/report/test_report_payload_builder.py \
  tests/services/report/test_report_service_market_mode.py \
  tests/services/report/test_report_service_member_count.py -q
```

结果：

- `39 passed`

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/report/report_context_loader.py \
  backend/app/services/report/report_service.py \
  backend/tests/services/report/test_report_context_loader.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

- 现在报告链前半段“谁能看、任务是否完整、analysis 是否可用”开始有单独真相源了。
- `ReportService.get_report()` 更像真正的编排层，不再一进来就先自己背一条 access/context 主链。
- 这一步继续把第三轮往 `95+` 的目标推进：
  - 主服务更薄
  - 门禁链更清楚
  - cache / validation / assembly 的边界更顺
  - 后面再改报告访问规则，不会再把整个 `get_report()` 一起拖回去

一句大白话：

- **这刀把报告链最前面那截“查任务、验权限、验会员”的门禁主链，也拆成独立齿轮了。**
