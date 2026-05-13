# Phase 321 - 第三轮继续打磨：execute_target 前置门禁链拆分

## 1. 发现了什么？

- `execute_target_workflow.py` 里还残留着一条很重的 preflight 主链：
  - 查 target 记录
  - claim running
  - 黑名单守卫
  - schema mismatch 提前 partial
  - 社区锁竞争处理
  - backfill running 状态切换
- 大白话说：
  - **主 workflow 还在一开始就自己兼任查单、验单、抢锁和预热工。**

## 2. 是否需要修复？

- 需要，而且已经修完。
- 这次没有改数据库表结构，没有新 migration。

## 3. 精确修复方法？

### 3.1 新增独立 preflight workflow

新增：

- `backend/app/services/crawl/execute_target_preflight.py`

正式收了：

- `ExecuteTargetPreflightContext`
- `ExecuteTargetPreflightInput`
- `ExecuteTargetPreflightDeps`
- `ExecuteTargetPreflightResult`
- `prepare_execute_target_preflight(...)`

把原来缠在主 workflow 前半段的这些动作收回到独立齿轮：

- `crawler_run_targets` 存在性检查
- target 记录查询与 missing-target audit
- queued -> running claim
- blacklist 守卫
- schema mismatch 提前 partial
- 社区锁竞争 + compensation
- backfill running 状态更新

### 3.2 收薄 execute_target_workflow

修改：

- `backend/app/services/crawl/execute_target_workflow.py`

现在：

- 主 workflow 不再自己手写整条 preflight 主链
- 改成先调用 `prepare_execute_target_preflight(...)`
- 拿到：
  - `early_payload`
  - 或 `preflight context`
- 然后才进入真正的 Reddit 执行主线

也就是：

- **主 workflow 继续往“只负责执行与编排”的方向收薄**

### 3.3 测试门禁

新增：

- `backend/tests/services/crawl/test_execute_target_preflight.py`

覆盖：

- missing target 会 audit 并返回失败
- community lock busy 会返回 partial 并生成 compensation

同时保留并补强：

- `backend/tests/services/crawl/test_execute_target_error_workflow.py`
- `backend/tests/services/crawl/test_execute_target_followup.py`
- `backend/tests/tasks/test_execute_target_task.py`

这样现在 `execute_target` 这条主链三层都被锁住了：

- preflight
- error
- followup

## 4. 验证结果

### 定向回归

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest \
  tests/services/crawl/test_execute_target_preflight.py \
  tests/services/crawl/test_execute_target_error_workflow.py \
  tests/services/crawl/test_execute_target_followup.py \
  tests/services/crawl/test_execute_target_workflow.py \
  tests/tasks/test_execute_target_task.py -q
```

结果：

- `27 passed`

### 主门禁

```bash
cd /Users/hujia/Desktop/RedditSignalScanner && SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

### 语法自检

```bash
python -m py_compile \
  backend/app/services/crawl/execute_target_preflight.py \
  backend/app/services/crawl/execute_target_workflow.py \
  backend/tests/services/crawl/test_execute_target_preflight.py
```

结果：

- 通过

## 5. 这次执行的价值是什么？达到了什么目的？

- 现在 `execute_target` 这条采集主链，已经不只是把错误收尾拆开了，连前置门禁链也开始有自己的独立齿轮了。
- 采集模块在第三轮里已经形成更完整的分层：
  - preflight
  - execute
  - error
  - followup
- 这一步继续把第三轮往 `95+` 的目标推进：
  - 主 workflow 更薄
  - 执行主线更纯
  - guard / execute / followup 边界更清楚
  - 后面再改锁、claim、黑名单和 compensation，不会再整段拖动执行主链

一句大白话：

- **这刀把数据采集模块最前面那截“查单、验单、抢锁”的门禁主链，也拆成独立齿轮了。**
