# Phase 380 - 第三轮大包推进：monitoring_task helper / runtime / wiring 成组收口

## 1. 发现了什么？

这次收的是 `backend/app/tasks/monitoring_task.py` 这一整包。

之前这块虽然监控逻辑已经开始说真话了，但 task 壳里还自己背着一整组 helper 和 runtime wiring：

- metrics redis 读取
- alert 发送
- e2e metrics 加载
- dashboard 写入
- route metrics 解码
- cache health 聚合入口
- api calls / contract health / dashboard / warmup 这些任务的依赖装配

大白话说：

- `monitoring_task.py` 还在一边当 Celery 入口，一边自己拼一整套监控运行时

这不符合第三轮现在的封板目标：

- task 壳继续变薄
- runtime / support 继续回服务层
- 单一真相源继续做硬

## 2. 是否需要修复？

需要，而且这次已经整包修完。

这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增 monitoring task support

新增：

- `backend/app/services/infrastructure/monitoring_task_support.py`

正式收走：

- `as_float / as_int`
- `get_metrics_redis(...)`
- `send_alert(...)`
- `load_e2e_metrics(...)`
- `update_dashboard(...)`
- `route_metrics_bucket(...)`
- `decode_int(...)`
- `load_route_call_metrics(...)`

也就是说：

- 通用 helper 不再继续堆在 task 壳里

### 3.2 新增 monitoring task runtime

新增：

- `backend/app/services/infrastructure/monitoring_task_runtime.py`

正式收走：

- `calculate_monitor_cache_health(...)`
- `run_monitor_api_calls(...)`
- `run_monitor_cache_health(...)`
- `run_update_performance_dashboard(...)`
- `run_monitor_e2e_tests(...)`
- `run_collect_test_logs(...)`
- `run_monitor_warmup_metrics(...)`
- `run_monitor_contract_health(...)`
- `build_monitoring_runtime_dependencies(...)`

大白话说：

- 监控任务怎么接 helper、怎么跑 runtime，现在开始有单独齿轮了

### 3.3 收薄 monitoring_task

修改：

- `backend/app/tasks/monitoring_task.py`

现在这文件主要只保留：

- Celery 入口
- 少量兼容 seam
- facts audit / crawler health / watchdog 这几条还没必要单拆的任务主体
- 对 support/runtime 的薄委托

顺手补平了两个真实问题：

1. `monitor_crawler_health()` / `watchdog_stalled_tasks()` 用到了 `select(...)`，原文件却没显式 import  
   这次已经补上

2. `test_monitoring_facts_audit.py` 之前把历史 backlog 也一起算进断言  
   这次改成先读 baseline，再验证“本轮新增的 1+1”

### 3.4 补测试锁边界

新增：

- `backend/tests/services/infrastructure/test_monitoring_task_runtime.py`

覆盖了：

- monitor api calls runtime
- performance dashboard runtime
- collect test logs runtime
- runtime deps factory 注入

同时继续跑通：

- `backend/tests/tasks/test_monitoring_task.py`
- `backend/tests/tasks/test_monitoring_facts_audit.py`
- `backend/tests/tasks/test_task_watchdog_stalled_tasks.py`

## 4. 验证结果

### 4.1 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/tasks/test_monitoring_task.py \
  tests/tasks/test_monitoring_facts_audit.py \
  tests/tasks/test_task_watchdog_stalled_tasks.py \
  tests/services/infrastructure/test_monitoring_task_runtime.py -q
```

结果：

- `13 passed`

### 4.2 主门禁

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 4.3 语法自检

```bash
python -m py_compile \
  backend/app/tasks/monitoring_task.py \
  backend/app/services/infrastructure/monitoring_task_support.py \
  backend/app/services/infrastructure/monitoring_task_runtime.py \
  backend/tests/services/infrastructure/test_monitoring_task_runtime.py \
  backend/tests/tasks/test_monitoring_facts_audit.py
```

结果：

- 通过

### 4.4 文件体量变化

- `backend/app/tasks/monitoring_task.py`：`728 -> 572`

## 5. 下一步系统性的计划是什么？

第三轮继续按“大包封板”推进，不再碎跑。

当前剩下最值钱的两包还是：

1. `数据采集模块` 最后一包清尾
2. `语义 / 标签模块` 最后一包清尾

然后做：

3. 第三轮总复盘  
   正式判断当前系统是否已经稳定站上 `95+`

## 6. 这次执行的价值是什么？达到了什么目的？

这次的价值很直接：

- `monitoring_task` 不再自己背一整套 helper + runtime wiring
- 监控任务开始真正像：
  - task 壳负责入口
  - support 负责通用能力
  - runtime 负责监控链编排

一句大白话总结：

- 这一步不是又拆一个小 helper，而是把监控模块里整包运行时真正抽回基础设施层了。第三轮现在已经非常接近最后收官。
