# Phase 305 - 第三轮第三刀：数据采集模块目标执行 workflow 独立

> 时间：2026-03-15  
> 模块：数据采集模块  
> 范围：`crawl_execute_task`、目标执行主链、补偿/状态/副作用编排  
> 当前状态：已完成第三轮第三刀

---

## 1. 发现了什么？

第三轮进入数据采集模块后，这一刀没有继续盯 comments ingest，而是直接打最重的那条链：

1. **`crawl_execute_task.py` 里的 `_execute_target_impl()` 还背着整条执行 workflow**
   - target claim
   - 黑名单守卫
   - 社区锁
   - backfill 状态切换
   - Reddit 执行
   - timeout / budget exhausted / partial / failed / completed 收尾
   - compensation target
   - evaluator / candidate vetting 副作用

2. **task 壳知道太多执行细节**
   - 这会让后面继续改执行策略、补偿策略、状态合同的时候，一改就是整大段
   - AI 和人也都更容易在这个文件里继续缠逻辑

一句大白话：

- **第一轮让执行结果开始说真话，第二轮拆了派发层，第三轮这一刀继续把“目标执行 workflow”从 task 壳里拆出去。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。  
这轮做的是结构性拆分，不是采集策略改版。

---

## 3. 精确修复方法？

### 3.1 新增正式执行 workflow 层

新增：

- `backend/app/services/crawl/execute_target_workflow.py`

收口了原来挂在 `crawl_execute_task.py` 里的主执行链：

- `ExecuteTargetWorkflowDeps`
- `ExecuteTargetWorkflowResult`
- `execute_target_workflow(...)`

这一步的核心不是“把代码搬家”，而是把任务执行这件事正式定义成：

- 一组明确依赖
- 一条明确 workflow
- 一个明确结果合同

### 3.2 `crawl_execute_task.py` 收成薄入口

修改：

- `backend/app/tasks/crawl_execute_task.py`

现在 `_execute_target_impl()` 不再自己背整条执行链，而是：

1. 组装 deps
2. 调 `execute_target_workflow(...)`
3. 返回 `result.as_dict()`

这样 task 壳保住了：

- 原任务名
- 原测试 monkeypatch seam
- 原返回合同

但执行主链已经不再继续长在 task 文件里。

一句大白话：

- **task 现在更像入口，workflow 开始更像独立齿轮。**

### 3.3 先补服务层测试，再用旧任务测试锁兼容

新增：

- `backend/tests/services/crawl/test_execute_target_workflow.py`

先把新的 workflow 边界锁住：

- 缺目标时会审计并返回 `target_missing`

同时继续复用并跑通原有：

- `backend/tests/tasks/test_execute_target_task.py`

这一步很关键，因为它说明：

- 我们不是把旧行为打碎重来
- 而是把旧行为搬进了新边界，并保持兼容

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“多一个 service 文件”，而是：

- `crawl_execute_task.py` 不再继续背最重的执行主链
- 目标执行 workflow 开始有自己的正式边界
- 后面继续拆补偿、副作用、状态协议，会顺很多

一句大白话：

- **这刀把采集模块里最重的那条“目标执行链”先抽成了独立齿轮。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_execute_target_workflow.py \
  tests/tasks/test_execute_target_task.py -q
```

结果：

- `19 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/execute_target_workflow.py \
  backend/app/tasks/crawl_execute_task.py \
  backend/tests/services/crawl/test_execute_target_workflow.py
```

结果：

- 通过

---

## 6. 结构结果

这刀之后，体感很直白：

- `crawl_execute_task.py` 从 `1295` 行降到 `677` 行
- `execute_target_workflow.py` 新增 `748` 行，专门承接目标执行主链

也就是说：

- **task 壳明显变薄了**
- **执行 workflow 真正开始独立了**

---

## 7. 这轮之后还剩什么？

数据采集模块第三轮这一刀之后，还剩几个继续值得打磨的点：

1. `crawl_execute_task` 里的辅助 helper 还偏多
2. 补偿 / evaluator / candidate vetting 副作用，后面还可以继续拆
3. `crawler_task` 和 `crawl_execute_task` 之间的调度-执行边界，还能继续压薄

所以这轮的正确定位是：

- **第三轮第三刀已经把目标执行主链拆出来了**
- 但不是数据采集模块第三轮全部完成

---

## 8. 下一步系统性的计划是什么？

按第三轮既定节奏，下一步进入：

- **社区治理模块** 或 **语义/标签模块** 的下一刀打磨

优先原则不变：

- 继续打最重的耦合点
- 继续把主链和副作用拆回各自边界
- 继续让整机从“可信、顺滑”往“接近产品级稳定”推进

一句话：

- **这刀先把数据采集模块最重的执行链拆开，下一步继续打下一组最重齿轮。**
