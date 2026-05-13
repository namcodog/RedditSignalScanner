# phase841 - SociaVault fallback 验证与 30 张 freshness 复核

## 发现

- 已完成 `SociaVault` 最小 Reddit fallback 接入验证，策略为：
  - Reddit 官方 API 仍是主路
  - 遇到 `429 / timeout / low-quota comment fetch` 时，再落到 `SociaVault`
- 这次不是纸面接入，已确认真实发生 credits 消耗。
- 但当前 `30` 张整批发布仍然不能直接放行，阻塞点仍是 freshness，不是 growth winner path，也不是旧 `15-baseline`。

## 代码改动

- 新增配置：
  - `backend/app/core/config.py`
    - `SOCIAVAULT_API_KEY`
    - `SOCIAVAULT_BASE_URL`
    - `SOCIAVAULT_REDDIT_FALLBACK_ENABLED`
- 新增客户端：
  - `backend/app/services/infrastructure/sociavault_reddit_client.py`
  - `backend/app/services/infrastructure/reddit_collect_client.py`
- collector 接入 fallback：
  - `backend/app/services/hotpost/source_scope_candidate_collector.py`
  - `backend/app/services/hotpost/named_topic_candidate_collector.py`
- 新增/更新测试：
  - `backend/tests/services/infrastructure/test_reddit_collect_client.py`
  - `backend/tests/services/infrastructure/test_sociavault_reddit_client.py`
  - `backend/tests/services/hotpost/test_source_scope_candidate_collector.py`
  - `backend/tests/services/hotpost/test_named_topic_candidate_collector.py`

## 真实验证

### API 可用性

- `SociaVault /v1/credits` 可用
- 认证方式：`x-api-key`
- base：`https://api.sociavault.com/v1`

### 回归测试

- `pytest backend/tests/services/infrastructure/test_reddit_collect_client.py backend/tests/services/infrastructure/test_sociavault_reddit_client.py`
  - `6 passed`
- 此前 collector 侧改动回归：
  - `16 passed`

### 30 张 freshness 复核

- 跑法：
  - `run_intake_freshness_gate --limit 30`
  - 开启 `SOCIAVAULT_REDDIT_FALLBACK_ENABLED=1`
- 说明：
  - gate 原脚本在这轮 full collect 中仍较慢，因此额外对生成的 `offline-publish-plan-30-sv3.json` 直接跑了同口径 freshness evaluator 做手工复核。

#### credits 消耗

- 验证开始前 credits：`19752`
- 最终复核后 credits：`19679`
- 本轮累计消耗：`73 credits`

#### 结果文件

- `backend/tmp/offline-publish-plan-30-sv3.json`
- `backend/tmp/intake-freshness-30-sv3-manual.json`

#### freshness 结果

- `decision = fail`
- 关键信号：
  - `lane_counts = hot 8 / breakdown 13 / signal 9`
  - `target_fresh_counts = hot 3 / breakdown 12 / signal 4`
  - `acceptable_fresh_counts = hot 4 / breakdown 13 / signal 5`
  - `stale_ratio = 0.2667`
  - `hot_freshness_pass = false`
  - `signal_freshness_pass = false`
  - `breakdown_freshness_pass = true`

## 结论

- `SociaVault` 作为 Reddit fallback 是有效的：
  - 已真实接管部分请求
  - 已开始实际消耗 credits
  - 能补官方 Reddit 的 `429 / comment timeout / low-quota` 场景
- 但它**还不足以把今天的 30 张整批 freshness 直接拉到可发布状态**。
- 当前更准确的运营结论：
  - 不应直接发 `30`
  - 如果今天要发，应继续走 `value-threshold publishing`
  - 以当前 fresh / acceptable-fresh 的实际库存滚动分批，而不是硬凑 30

## 下一步

1. 保留这套 `Reddit main + SociaVault fallback` 路径
2. 继续按 freshness gate 决定每一批实际可发量
3. 如果仍要冲更高日内总量，下一步应收：
   - collect 宽度
   - comment timeout
   - quota-aware batching
   而不是回退 growth winner path
