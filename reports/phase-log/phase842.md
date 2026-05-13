# Phase 842 - quota-aware yield-until-exhausted crawl rollout

## 1. 发现了什么？

- 当前 Reddit intake 的主问题不是关键词不够，而是采集调度仍然是“一次性广撒网 + candidate 阶段同步评论 enrichment”。
- 这会直接把 freshest `hot / signal` 的发现优先级打掉，并把评论压力过早压到 Reddit 官方 API 上。
- 新合同已经统一为：
  - `Reddit API = freshest hot/signal 主采`
  - `SociaVault = assist + rescue`
  - `discover -> enrich -> backfill`
  - `dry_cycle = 3`
  - 停机口径改成 `yield exhaustion`

## 2. 是否需要修复？

- 需要。
- 这轮不动 prompt / schema / planner / publish plan / mini snapshot / named topic。
- 只改 intake / collect 调度链。

## 3. 精确修复方法？

### 代码改动

- 配置与合同：
  - `backend/config/hotpost_supply_discovery_v2.yaml`
  - `backend/app/services/hotpost/hotpost_supply_contract.py`
- 新增 crawl contract helper：
  - `backend/app/services/hotpost/quota_aware_crawl.py`
  - `backend/app/services/hotpost/quota_aware_collect_runner.py`
- collect 调度链：
  - `backend/app/services/hotpost/source_scope_candidate_collector.py`
  - `backend/app/services/hotpost/candidate_spec_collector.py`
  - `backend/scripts/hotpost/daily_collect.py`
  - `backend/scripts/hotpost/run_intake_freshness_gate.py`
- SociaVault assist/rescue：
  - `backend/app/services/infrastructure/reddit_client.py`
  - `backend/app/services/infrastructure/reddit_collect_client.py`

### 当前实现

- Pass 1 `discover`
  - 只跑 discover specs
  - 只拿帖子，不同步抓评论
- Pass 2 `enrich`
  - 只给 shortlist 的 `hot/signal` 补评论
  - 评论压力在 low-quota / timeout 时优先落到 SociaVault
- Pass 3 `backfill`
  - 最后才跑剩余 backfill specs
  - 不再 candidate 阶段全量评论 enrichment
- Stop rule
  - `daily_collect.py` 和 `run_intake_freshness_gate.py` 都改成走 `run_quota_aware_collect`
  - 连续 `3` 个 dry cycle 无新增 publishable gain 即停

### SociaVault 介入触发器

- `429`
- timeout / connection failed
- low quota 导致 comment fetch 应跳过
- `dry_cycles >= 2` 时允许 discover 面开启 assist

## 4. 验证结果

- `python -m py_compile ...`：通过
- 回归测试：
  - `21 passed`
- 新增覆盖点：
  - 评论 enrichment 只发生在 shortlist
  - collect 顺序固定为 `discover -> enrich -> backfill`
  - `dry_cycle = 3` 会按 yield exhaustion 停止
  - low-quota discover assist 会打开 SociaVault post rescue

### 轻量实证

当前 spec 切相结果：

- `ai-automation`
  - `discover = 40`
  - `backfill = 179`
- `business-growth-ops`
  - `discover = 36`
  - `backfill = 90`
- `ecommerce-sellers`
  - `discover = 24`
  - `backfill = 243`

说明当前项目侧已经先把 freshest discover 面从大 backfill 面里拆出来，不再一上来全量扫。

### 单 scope 真实样本

运行：

- `python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --mode safe --dry-cycle 3`

结果：

- `3` 个 cycle 后按 `yield_exhaustion` 自停
- 每轮 `imported = 9`
- `publishable_total` 没有继续增长，按合同进入 `dry_cycle = 3`
- 运行中出现的是局部 `request timeout`，不是整轮崩溃
- 说明新调度当前已经满足：
  - 可以持续 crawl
  - 不靠固定 `15/30` 停机
  - 遇到无新增收益时会自动停

## 5. 下一步系统性的计划是什么？

- 先按这条新 crawl 合同跑夜间稳态任务。
- 下一轮真实运营只继续看：
  - freshest `hot / signal` 发现效率
  - `429` 是否下降
  - comments 是否更集中在 shortlist
  - SociaVault credits 是否主要消耗在 assist / rescue 位

## 6. 这次执行的价值是什么？

- 这轮不是再调 query，也不是再顶并发。
- 真正达成的是：把采集从“固定数量 + 早评论 + 广撒网”切到“业务优先级驱动 + 评论后置 + yield exhaustion 停机”的新合同。
