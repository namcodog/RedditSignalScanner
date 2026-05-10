# Phase 299 - 基础设施/监控模块第二轮第一刀：contract health workflow 服务化

> 时间：2026-03-15
> 模块：基础设施 / 监控模块
> 范围：contract health 聚合、dashboard/audit 副作用、task 壳瘦身
> 当前状态：已完成第二轮第一刀

---

## 1. 发现了什么？

第二轮回到基础设施 / 监控模块后，这一刀没有继续补状态字段，而是先盯住了最重的那条监控链：

- `monitor_contract_health()`

查下来它虽然第一轮已经开始说真话了，但 task 层仍然背着太多事：

1. 读取 `tasks + analysis.sources`
2. 组装 `ContractHealthRow`
3. 计算 report / alerts
4. 写 dashboard
5. 发送 alerts
6. 写 audit events
7. 最后再拼 payload

一句大白话：

- **第一轮把监控开始收成“说真话”，第二轮这一刀开始把最重的 workflow 从 task 层拆回基础设施服务层。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这一刀做的是结构性收口，不是监控规则改版。

---

## 3. 精确修复方法？

### 3.1 新增正式 workflow 服务

新增：

- `backend/app/services/infrastructure/contract_health_workflow.py`

这层正式接管了 contract health 这条监控 workflow，新增了：

- `load_contract_health_rows(...)`
- `build_contract_health_result(...)`
- `finalize_contract_health_result(...)`

职责拆分后变成：

1. **加载 rows**
2. **生成正式 `ContractHealthResult`**
3. **统一做 dashboard / alert / audit 副作用收尾**

这意味着现在不是：

- task 自己把聚合、输出、副作用全包了

而是：

- **workflow service 负责整条 contract health 编排**
- **task 只负责参数、运行、统一返回**

### 3.2 monitoring task 退回 orchestration shell

修改：

- `backend/app/tasks/monitoring_task.py`

这次把 `monitor_contract_health()` 收成了薄入口：

1. 读 `window_hours`
2. 构造 `now / cutoff / thresholds`
3. 调 `build_contract_health_result(...)`
4. 调 `finalize_contract_health_result(...)`
5. 统一 `_serialize_monitoring_result(...)`

task 层不再自己：

- 拼 `ContractHealthRow`
- 算 alerts
- 手写 dashboard / audit 故障处理细节

一句大白话：

- **task 开始更像任务入口，不再自己当 workflow 引擎。**

### 3.3 测试分层锁住新边界

新增：

- `backend/tests/services/infrastructure/test_contract_health_workflow.py`

这组测试锁住了：

1. workflow 能基于 rows 正确产出 `ContractHealthResult`
2. audit 写失败时，finalizer 会把结果标成 `degraded`

同时修改：

- `backend/tests/tasks/test_monitoring_task.py`

task 层测试不再硬测整条编排细节，而是改成验证：

- task 是否能吃 workflow 结果
- task 是否能正确序列化 finalized result

这一步很重要，因为它避免了后面继续把：

- workflow 责任
- task shell 责任

又混回一层。

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮的价值不是“多了一个 service 文件”，而是：

- 把监控模块里最重的 contract health workflow 真正拆回了基础设施服务层
- 让 task 层开始更像 orchestration shell
- 让 dashboard / audit / alert 这类副作用开始围绕正式结果对象统一收口

这更符合第二轮目标：

- 职责更单一
- 接口更稳
- 高耦合点继续打薄

一句大白话：

- **这刀把监控模块里最容易越写越重的那条 contract health 链先拆开了，后面继续收 cache / dashboard / 监控编排时，会顺很多。**

---

## 5. 验证结果

### 定向 workflow + task 回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/infrastructure/test_contract_health_workflow.py \
  tests/tasks/test_monitoring_task.py -q
```

结果：

- `8 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/infrastructure/contract_health_workflow.py \
  backend/app/tasks/monitoring_task.py \
  backend/tests/services/infrastructure/test_contract_health_workflow.py \
  backend/tests/tasks/test_monitoring_task.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

基础设施 / 监控模块第二轮这一刀之后，还剩几个更大的结构问题没有做：

1. cache health 虽然已经比 contract health 薄，但计算链和 task 入口还能继续分层
2. dashboard 写入、alert 发送、metrics 汇总还可以继续朝统一 workflow 靠
3. 监控任务之间的结果合同虽然统一了，但 orchestrator / transport 边界还能继续打磨

所以这轮的正确定位是：

- **第二轮第一刀已经值回票价**
- 但不是基础设施 / 监控模块第二轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第二轮既定顺序，下一步进入：

- **API / 前端展示模块** 的第二轮结构性收口
