# Phase 539 - readiness / preflight 切到 truth-source

## 这轮目标

在 `community_governance` 之后，把报告主链里另外两条关键社区判断也切离旧表：

1. `analysis_readiness_support.build_data_readiness_snapshot`
2. `execute_target_task_support.load_community_blacklist_status`

这两条如果还留在旧 `community_cache / community_pool` 上，主链就依然不是单一真相源。

## 这轮改了什么

### 1. readiness 改成直读 truth-source

更新：

- `backend/app/services/analysis/analysis_readiness_support.py`

新口径：

- 社区存在性、当前归属、治理状态、运行状态
- 全部来自 truth-source 四表

具体规则：

- registry 不存在：`MISSING`
- registry disabled：`DISABLED`
- 缺 current membership：`MISSING_MEMBERSHIP`
- 未 approved：`UNAPPROVED`
- 缺 runtime：`MISSING_RUNTIME`
- 若 runtime_notes 中有 `backfill_status`，则直接使用该真实状态
- 若没有，则只暴露真实运行态：
  - `NEEDS`
  - `PAUSED`
  - `BLOCKED`
  - `ACTIVE_UNKNOWN`
  - `UNKNOWN`

没有再从旧 `community_cache` 兜底读取。

### 2. preflight 黑名单改成直读 truth-source

更新：

- `backend/app/services/crawl/execute_target_task_support.py`

新口径：

- 是否 blocked，不再查 `community_pool.is_blacklisted`
- 改成查 current membership + current governance decision
- 只要当前治理决策是 `blocked`，就阻断
- truth-source 不存在时返回 `None`，不伪造黑名单结果

## 测试与验证

### 定向测试

- `pytest backend/tests/services/analysis/test_analysis_readiness_support.py backend/tests/services/analysis/test_analysis_engine.py -q`
  - `52 passed`
- `pytest backend/tests/services/crawl/test_execute_target_task_support.py backend/tests/services/crawl/test_execute_target_preflight.py -q`
  - `5 passed`

### 组合回归

```bash
pytest \
  backend/tests/services/community/test_community_governance_service.py \
  backend/tests/api/test_admin_community_pool.py \
  backend/tests/services/analysis/test_analysis_readiness_support.py \
  backend/tests/services/analysis/test_analysis_engine.py \
  backend/tests/services/crawl/test_execute_target_task_support.py \
  backend/tests/services/crawl/test_execute_target_preflight.py -q
```

结果：

- `73 passed`

## 这轮没有做的事

- 没有给旧表再塞新的兜底逻辑
- 没有为了“看起来 ready”而伪造 `DONE_12M`
- 没有把缺 truth-source 的情况偷偷回退到 `community_cache / community_pool`

## 当前收口状态

到这一步，社区层已经有 3 条真实读路径切到 truth-source：

1. `community_governance`
2. `analysis_readiness_support`
3. `execute_target_task_support.blacklist`

## 剩余任务

现在剩余的大任务更聚焦了：

1. 继续切剩余主链社区判断到 truth-source
2. 旧表职责退役
3. Dev 物理压缩，真正把库收干净

## 这轮价值

这轮的价值不是“多过了 73 个测试”，而是：

- 主链中真正参与报告 readiness 和执行阻断的社区判断，已经开始统一到单一真相源
- 现在系统更接近“说真话的系统”，而不是“旧表和新表混着用的系统”
- 用户后面再切别的领域时，这条社区主链更有机会保持一致，而不是继续靠运气
