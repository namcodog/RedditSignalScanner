# Phase 295 - 数据采集模块第二轮第一刀：task_outbox 派发主循环下沉

> 时间：2026-03-15
> 模块：数据采集模块
> 范围：`crawler_task`、`task_outbox` 派发、基础设施服务边界
> 当前状态：已完成第二轮第一刀

---

## 1. 发现了什么？

第二轮回到数据采集模块后，最缠的一根线不是抓取算法本身，而是：

- `crawler_task.py` 里的 `task_outbox` 派发主循环

这段逻辑以前同时背了：

1. 批次参数读取
2. DB 取待派发事件
3. payload 校验
4. 环境指纹校验
5. `crawler_run_targets` 查询
6. Celery 下发
7. `task_outbox` sent/failed 更新
8. 最终状态汇总

而仓库里其实已经有：

- `backend/app/services/infrastructure/task_outbox_service.py`

也就是说：

- **服务边界已经有了**
- **但真正最重的派发主循环还留在 task 层**

一句大白话：

- **第一轮把采集模块的状态说真话了，第二轮这一刀开始把“派发怎么做”从任务入口里拆回服务层。**

---

## 2. 是否需要修复？

需要，而且这一步已经修完。

这次没有改数据库 schema，没有新增 migration。
这轮做的是结构性收口，不是抓取逻辑改版。

---

## 3. 精确修复方法？

### 3.1 新增正式 outbox 派发服务

新增：

- `backend/app/services/infrastructure/task_outbox_dispatcher.py`

新增正式结果对象：

- `TaskOutboxDispatchResult`

新增正式派发入口：

- `dispatch_pending_task_outbox(...)`

这层现在统一负责：

- 取待派发 outbox
- 校验 payload / target / env fingerprint
- 处理 `backfill_posts` 队列切换
- 发送 Celery 任务
- 更新 `crawler_run_targets.enqueued_at`
- 更新 `task_outbox` sent / failed
- 汇总：
  - `idle`
  - `completed`
  - `degraded`
  - `failed`

也就是说：

- **task_outbox 派发的业务动作，现在终于回到了基础设施服务层。**

### 3.2 `crawler_task.py` 收成更薄的入口

修改：

- `backend/app/tasks/crawler_task.py`

这次把 `_dispatch_task_outbox_impl()` 从“大循环亲自干活”收成了：

1. 读取批次参数
2. 调用 `dispatch_pending_task_outbox(...)`
3. commit
4. 返回统一结果

同时顺手删掉了 task 层不该继续背的内部细节：

- `_summarize_outbox_dispatch_status(...)`
- `_normalize_outbox_payload(...)`

结果是：

- `crawler_task.py` 从 `1726` 行降到 `1570` 行

一句大白话：

- **现在 task 层更像任务入口，派发细节回到 service 层了。**

### 3.3 补服务层门禁测试

新增：

- `backend/tests/services/infrastructure/test_task_outbox_dispatcher.py`

覆盖了两个最小但关键的服务层合同：

1. 没有待派发事件时返回 `idle`
2. payload 缺 `target_id` 时显式 `failed`

同时保留原有 task 层回归：

- `backend/tests/tasks/test_task_outbox_dispatcher_task.py`
- `backend/tests/tasks/test_execute_target_task.py`

这样现在不是只测“task 看起来还能跑”，而是：

- **服务边界本身也有测试锁住。**

---

## 4. 这次执行的价值是什么？达到了什么目的？

这轮价值不是“又多一个服务文件”，而是：

- 把 `crawler_task` 里最像基础设施派发器的一坨逻辑，真正挪回基础设施服务层
- 让 task 层只负责“入口 + orchestration”
- 让 outbox 派发层自己承担自己的职责

这更符合第二轮目标：

- 职责更单一
- 接口更稳
- 高耦合点继续打薄

一句大白话：

- **这刀把采集模块里最重的派发循环先拆开了，后面再拆 planner / executor / ingest 会顺很多。**

---

## 5. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/infrastructure/test_task_outbox_dispatcher.py \
  tests/tasks/test_task_outbox_dispatcher_task.py \
  tests/tasks/test_execute_target_task.py -q
```

结果：

- `23 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/infrastructure/task_outbox_dispatcher.py \
  backend/app/tasks/crawler_task.py \
  backend/tests/services/infrastructure/test_task_outbox_dispatcher.py
```

结果：

- 通过

---

## 6. 这轮之后还剩什么？

数据采集模块第二轮这一刀之后，还剩几个更大的结构问题没有做：

1. `crawler_task.py` 本体仍然偏大
2. planner / dispatcher / execute / ingest 之间还能继续拆边界
3. `crawl_execute_task.py` 也还是一个偏重文件

所以这轮的正确定位是：

- **第二轮第一刀已经值回票价**
- 但不是数据采集模块第二轮全部完成

---

## 7. 下一步系统性的计划是什么？

按第二轮既定顺序，下一步进入：

- **社区治理模块** 的第二轮结构性收口

重点会从第一轮的“真相源和治理视图清楚”，继续推进到：

- 快照 / 动作边界继续拆清
- 历史壳隔离合同继续变硬
- 控制面和治理服务的职责继续收口

一句话：

- **数据采集模块这刀先收到这里，下一步回到源头治理层继续拆耦合。**
