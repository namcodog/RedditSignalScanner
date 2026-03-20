# Phase 264 - Round 4 第一阶段深修（监控 + 基础设施）

## 目的
- 先把 Round 4 里优先级最高的“假健康 / 假成功”问题收一轮
- 重点只修两条线：
  - `monitoring_task.py`
  - `services/infrastructure/*`
- 同时顺手做文件瘦身，避免长函数继续膨胀

## 这轮修了什么

### 1. 监控不再“表面正常、实际降级”
- `monitor_cache_health()`
  - 以前：实体率统计失败、维护任务失败后，只打 warning，返回值看起来还是正常
  - 现在：会明确返回 `status=degraded`，并带 `degraded_checks`
- `monitor_contract_health()`
  - 以前：dashboard 写入失败、审计事件写入失败会被 best-effort 吞掉，外面看不出这次监控本身已经降级
  - 现在：会明确标成 `degraded`，不再伪装成完整成功
- `monitor_facts_audit_cleanup()`
  - 把 `NOW()` 改成 Python 先算当前时间再传 SQL 参数，避免这层继续留“当前时间 SQL”口子

### 2. Reddit 客户端不再把真实失败压成空结果
- `RedditAPIClient._request_json()`
  - 以前：超时、坏 JSON、连接失败，很多情况会直接退 `{}`，调用方分不清是真空数据还是请求失败
  - 现在：
    - `403/404` 仍视为“空资源”，继续返回空
    - 超时 / 坏 JSON / 连接失败 / 持续 429 / 服务端错误，都会变成明确的 `RedditAPIError`
- `fetch_post_comments()`
  - 对评论场景继续保留“尽量给部分结果”的策略
  - 但现在是**显式接住** `RedditAPIError` 再降级成空，不再靠底层偷偷返回空字典

### 3. 顺手收了基础设施里的 `NOW()`
- `scheduler_service.py`
- `subreddit_snapshot.py`
- `monitoring_task.py`

## 结构收口
- 新增了辅助模块：
  - `backend/app/services/infrastructure/monitoring_support.py`
- 目的不是分散逻辑，而是把监控任务里新加的辅助逻辑单独收纳
- 结果：
  - `monitoring_task.py` 从 **836 行降到 792 行**
  - 监控主任务函数更短，也更容易测

## 测试
- 定向回归：
  - `cd backend && SKIP_DB_RESET=1 python -m pytest tests/tasks/test_monitoring_task.py tests/services/infrastructure/test_reddit_client.py tests/services/infrastructure/test_reddit_client_robustness.py tests/services/infrastructure/test_reddit_client_fail_fast_global_limiter.py tests/services/infrastructure/test_reddit_client_proxy.py -q`
  - `13 passed`
- 质量门禁：
  - `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`
- AST：
  - 已通过

## 当前统一口径
- 监控任务现在开始说真话了：
  - `ok`：完整成功
  - `degraded`：主流程还活着，但子步骤失败了
  - `error`：这次监控本身没跑成
- Reddit API 客户端现在也开始说真话了：
  - 真空资源：空
  - 真请求失败：抛明确错误
  - 需要降级的上层，必须自己显式接住再降级

## 还没做的
- Round 4 还剩两块没动：
  - `LLM` 链路
  - `hotpost` 链路
- 下一步应该继续按既定顺序推进：
  1. `openai_client.py` + `llm_label_task.py`
  2. `hotpost/service.py` + `query_resolver.py` + `report_llm.py`

## 结论
- Round 4 第一阶段深修已完成
- 当前状态应定义为：
  - **Round 4 已审计**
  - **第一阶段（监控/基础设施）已深修完成**
  - **LLM / hotpost 待继续**
