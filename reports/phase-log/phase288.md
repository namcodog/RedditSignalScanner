# Phase 288 - 基础设施 / 监控模块第一轮整治：监控结果正式建模，接口不再各说各话

> 时间：2026-03-15  
> 模块：基础设施 / 监控模块  
> 范围：`monitoring_task.py`、`monitoring_support.py`、监控模块定向测试  
> 当前状态：已完成第一轮

---

## 1. 发现了什么？

这轮没有重复去修 Round 4 已经收过的“假健康”问题，而是继续往更深一层看：

- `monitor_cache_health()` 和 `monitor_contract_health()` 现在已经开始说真话
  - `ok`
  - `degraded`
  - `error`
- 但它们对外还是在返回各自拼出来的 `dict[str, Any]`
- `generated_at`、`degraded_checks`、`message` 这些核心字段，没有正式 schema 合同
- 测试也只能按散字段在盯

这就带来一个很典型的问题：

- 监控任务已经比以前诚实了
- 但**“怎么把诚实结果返回出去”**这件事，还没有统一接口

一句大白话：

- **现在监控这组任务已经会说真话，但它们还是各自拿字典在说，接口真相源还没锁住。**

这和前面几个模块的第一轮深修问题是同类的：

- 文档说清楚了不够
- 代码接口也必须统一
- 测试还要把这层锁死

---

## 2. 是否需要修复？

需要，而且这轮已经修完第一刀。

这次没有改数据库 schema，也没有新增 migration。  
做的是三件事：

1. 给监控任务结果新增正式 schema
2. 让两个最关键的监控任务都走统一结果合同
3. 保持对外仍返回普通 JSON，避免大面积打碎现有调用方

---

## 3. 精确修复方法？

### 3.1 新增监控结果 schema

新增：

- `backend/app/schemas/monitoring.py`

核心模型：

- `MonitoringTaskResult`
- `MonitoringDegradedCheck`
- `MonitoringAlertPayload`
- `CacheHealthResult`
- `ContractHealthResult`

这一层的意义不是“多几个类”，而是把监控任务最核心的对外合同正式定下来：

- `status`
- `generated_at`
- `message`
- `degraded_checks`

并且针对两个关键任务补出专属字段：

- cache health
- contract health

也就是说：

- **这组任务不再只是“大家约定都这么返回”，而是正式进入代码接口合同。**

### 3.2 监控 support 层新增统一序列化与错误返回 helper

修改：

- `backend/app/services/infrastructure/monitoring_support.py`

新增：

- `build_monitoring_error_result(...)`
- `serialize_monitoring_result(...)`

并把 `mark_payload_degraded(...)` 升级成：

- 既能处理旧 dict
- 也能处理新的 `MonitoringTaskResult`

这一步很关键，因为它保证了：

- 新合同能落地
- 老的测试桩/调用方也不会被一刀切打爆

一句话：

- **统一合同落地了，但兼容层也留住了，节奏没炸。**

### 3.3 两个最关键的监控任务改走统一合同

修改：

- `backend/app/tasks/monitoring_task.py`

#### `monitor_cache_health()`

原来：

- `_calculate_monitor_cache_health()` 返回 dict
- 错误场景也直接手拼 `{"status": "error", "message": ...}`

现在：

- `_calculate_monitor_cache_health()` 返回 `CacheHealthResult`
- 包含统一的：
  - `status`
  - `generated_at`
  - `degraded_checks`
- 任务出口再统一 `model_dump(mode="json")`

#### `monitor_contract_health()`

原来：

- `_load()` 返回 dict
- 聚合失败时直接手拼错误结果

现在：

- `_load()` 返回 `ContractHealthResult`
- 任务出口统一序列化
- 错误场景统一走 `build_monitoring_error_result(...)`

也就是说：

- **这两个最关键的监控任务，已经从“各自发明结果字典”，收成了“同一套正式输出协议”。**

### 3.4 测试门禁补齐

修改：

- `backend/tests/tasks/test_monitoring_task.py`

新增/补强验证：

1. `monitor_cache_health()` 降级结果必须带：
   - `generated_at`
   - `degraded_checks`
2. `monitor_cache_health()` 错误结果也必须走统一合同

这样以后谁再把监控结果改回随手拼 dict，测试会直接红。

---

## 4. 这轮结果是什么？

这轮的本质不是“监控功能更多了”，而是：

- **监控任务现在不仅开始说真话，而且开始用同一种接口说真话。**

这更符合系统总整治的准则：

- 各模块职责清楚
- 通过统一接口协同
- 彼此少牵连
- 整条链路顺畅可控

一句大白话：

- **这轮把基础设施 / 监控模块从“状态比以前诚实，但接口还是散的”，收成了“状态和接口开始一起统一”。**

---

## 5. 验证结果

### 监控 / 基础设施定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/tasks/test_monitoring_task.py \
  tests/services/infrastructure/test_reddit_client.py \
  tests/services/infrastructure/test_reddit_client_robustness.py \
  tests/services/infrastructure/test_reddit_client_fail_fast_global_limiter.py \
  tests/services/infrastructure/test_reddit_client_proxy.py -q
```

结果：

- `14 passed`

### 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

---

## 6. 这轮还暴露了什么残留点？

这轮第一刀已经把“监控输出合同”收住了，但基础设施 / 监控模块还留着两个后续值得继续看的点：

1. `monitoring_task.py` 仍然偏大  
   - 第一轮先统一合同
   - 第二轮如果继续做，更适合往职责拆分走

2. 模块里仍有一批“较小任务”没接入正式 schema  
   - 这轮只先收最关键的两类：
     - `monitor_cache_health`
     - `monitor_contract_health`
   - 后面如果继续推进，可以按同样方法逐步把别的监控任务也收进统一合同

一句话：

- **这轮先把最关键的监控输出协议锁住了；下一轮如果继续做，重点会是把更多任务纳入同一套结果合同，并继续给 `monitoring_task.py` 减耦。**

---
