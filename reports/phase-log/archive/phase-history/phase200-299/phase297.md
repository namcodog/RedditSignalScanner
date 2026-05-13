# Phase 297 - 语义/标签模块第二轮第一刀：评论候选规划服务化

> 时间：2026-03-15
> 模块：语义 / 标签模块
> 范围：在线评论打标签、离线历史激活导出、候选规划服务边界
> 当前状态：已完成第二轮第一刀

---

## 1. 发现了什么？

第二轮回到语义 / 标签模块后，这一刀没有继续调 prompt，也没有去改 LLM client，而是先盯住了这条真正最值钱的链：

- **评论候选是怎么被挑出来的**

查下来最深的问题是：

1. 在线 `llm_label_task` 自己用 SQL 拉一套评论候选
2. 离线 `export_llm_label_candidates.py` 又自己算一套历史激活评论
3. 两边虽然共享了少量 prefilter 函数，但“到底哪些评论值得进入标签链”并没有真正收成同一条规划链

更具体一点：

- `export_llm_label_candidates.py` 还在直接 import：
  - `backend/app/tasks/llm_label_task.py` 里的私有常量和私有 helper
- 也就是：
  - **脚本层直接反向依赖 task 层**
  - **在线和离线候选规划仍然是高耦合状态**

一句大白话：

- **第一轮把语义/标签模块的状态协议收住了，第二轮这一刀开始把“评论到底怎么被选进标签链”收成正式服务边界。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这轮做的是结构性收口，不是标签算法改版。

---

## 3. 精确修复方法？

### 3.1 新增正式评论候选规划服务

新增：

- `backend/app/services/llm/comment_label_planner.py`

这层正式接管了两类规划职责：

1. **在线增量评论打标签规划**
   - `build_incremental_comment_label_plan(...)`
   - `build_incremental_comment_label_plan_from_rows(...)`

2. **离线历史激活评论规划**
   - `build_comment_activation_export_plan(...)`
   - `build_historical_comment_activation_plan(...)`

同时新增正式结果对象：

- `IncrementalCommentLabelPlan`
- `CommentActivationBatch`
- `HistoricalCommentActivationPlan`

这意味着现在不是：

- task 层算自己的候选
- script 层算自己的候选

而是：

- **评论候选规划先回到 service 层**
- **在线和离线都吃同一类正式结果对象**

### 3.2 在线任务退回 orchestration

修改：

- `backend/app/tasks/llm_label_task.py`

现在评论在线打标签不再自己：

- 写 SQL 拉评论候选
- 再自己做第一层规则筛选

而是改成：

1. 调 `build_incremental_comment_label_plan(...)`
2. 拿正式 `plan.candidates`
3. 再做 core / lab 长短链分桶、预算闸门和 LLM 调用

一句大白话：

- **task 层开始更像“执行入口”，不再自己兼任候选规划器。**

### 3.3 离线导出不再直接反向依赖 task 私有 helper

修改：

- `backend/scripts/report/export_llm_label_candidates.py`

这次把最关键的评论路径收掉了：

- 默认 comments 导出改成走 `build_incremental_comment_label_plan(...)`
- historical activation 改成走 `build_historical_comment_activation_plan(...)`
- 纯内存配额/批次构造改成走 `build_comment_activation_export_plan(...)`

这样现在不是：

- script import task 私有函数拼流程

而是：

- **script 只做 CLI 和写文件**
- **真正的候选规划逻辑回到 service 层**

### 3.4 测试把新边界锁住

新增：

- `backend/tests/services/llm/test_comment_label_planner.py`

修改：

- `backend/tests/tasks/test_llm_label_task.py`
- `backend/tests/scripts/test_export_llm_label_candidates.py`

测试现在锁住了三件事：

1. 增量候选规则层会过滤短评论 / 去重 / 跳过 noise
2. 历史激活配额和分批计划会稳定输出
3. 在线 task 和离线 exporter 都已经开始吃 planner 结果，而不是再各算各的

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“标签更准了”，而是：

- 把语义 / 标签模块里最容易继续漂移的“评论候选规划”真正抽成了独立齿轮
- 让在线任务和离线激活开始围绕同一个候选真相源协作

这更符合第二轮目标：

- 职责更单一
- 接口更稳
- 高耦合点继续打薄

一句大白话：

- **这刀把“评论该不该进入标签链”从任务和脚本里拆出来了，后面讨论标签价值、历史激活、离线 Codex 补标时，终于开始站在同一套口径上。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/llm/test_comment_label_planner.py \
  tests/tasks/test_llm_label_task.py \
  tests/scripts/test_export_llm_label_candidates.py -q
```

结果：

- `11 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/llm/comment_label_planner.py \
  backend/app/tasks/llm_label_task.py \
  backend/scripts/report/export_llm_label_candidates.py \
  backend/tests/tasks/test_llm_label_task.py \
  backend/tests/services/llm/test_comment_label_planner.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

语义 / 标签模块第二轮这一刀之后，还剩几个更大的结构问题没有做：

1. posts 标签链和 comments 标签链还没有完全并到统一规划边界
2. provider / import-export / semantic sync 之间还能继续拆职责
3. 真正的“标签价值激活”和“离线补标执行节奏”还属于后续专项，不在这轮结构收口里一起展开

所以这轮的正确定位是：

- **第二轮第一刀已经值回票价**
- 但不是语义 / 标签模块第二轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第二轮既定顺序，下一步进入：

- **hotpost 模块** 的第二轮结构性收口

重点会从第一轮的“状态说真话、debug_info 正式建模”，继续推进到：

- query / resolver / result bundle 边界继续拆清
- 缓存、实时结果、fallback 之间的编排层继续收口
- 输出壳继续变薄

一句话：

- **语义 / 标签模块这刀先收到这里，下一步继续回到输出表达层拆耦合。**
