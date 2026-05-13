# Phase 738 - Reddit 账号保护护栏落地

## 发现了什么

- 当前 collect 的主风险已经不是单次失败，而是 Reddit `429` 和评论接口超时会持续拖慢整轮抓取，继续硬打有账号风险。
- 现有实现里，`X-Ratelimit-Reset` 被按 Unix 时间戳理解，这会让退避判断失真。
- collect 侧虽然已经有“单个 spec 失败不拖死整轮”和“评论去重”，但还缺一层真正的账号保护：
  - 低配额自动降速
  - 连续 `429` 自动加大冷却
  - 低配额时停止评论补抓

## 是否需要修复

- 需要，而且优先级高于继续扩 collect 面。
- 原因不是“多抓点再说”，而是先保证 Reddit 账号安全，再谈稳定收割。

## 精确修复方法

### 1. Reddit 客户端护栏

文件：
- `backend/app/services/infrastructure/reddit_client.py`

已落地：
- `X-Ratelimit-Reset` 改为按“距离重置还有多少秒”解释，不再按 Unix 时间戳解析
- 新增低配额护栏参数：
  - `low_quota_remaining_threshold`
  - `low_quota_cooldown_seconds`
  - `stop_comment_fetch_below_remaining`
  - `max_consecutive_rate_limit_errors`
- `_throttle()` 现在会在低配额时主动冷却，而不是继续以正常节奏打 Reddit
- 连续 `429` 达到阈值后，会把退避时间至少抬到低配额冷却时长
- 新增：
  - `should_skip_comment_fetch()`
  - `get_ratelimit_snapshot()`

### 2. collect 侧降级

文件：
- `backend/app/services/hotpost/source_scope_candidate_collector.py`

已落地：
- 创建 `RedditAPIClient` 时正式接入 YAML 护栏参数
- 如果当前 Reddit 配额偏低，collect 会跳过评论补抓，只保留帖子主信息导入候选
- 这样做的边界是：
  - 先保账号
  - 不让评论接口继续成为高频压力源

### 3. YAML 配置收口

文件：
- `backend/config/hotpost_supply_discovery_v2.yaml`
- `backend/app/services/hotpost/hotpost_supply_contract.py`

新增 collect 默认值：
- `low_quota_remaining_threshold: 12`
- `low_quota_cooldown_seconds: 20`
- `stop_comment_fetch_below_remaining: 18`
- `max_consecutive_rate_limit_errors: 3`

## 验证结果

### 定向测试

命令：

```bash
cd backend && pytest tests/services/infrastructure/test_reddit_client.py tests/services/hotpost/test_source_scope_candidate_collector.py -q
```

结果：
- `15 passed`

新增覆盖：
- `Reset` 头按秒解析
- 低配额自动冷却
- 低配额时 collect 停评论补抓

### 编译检查

命令：

```bash
python -m py_compile backend/app/services/infrastructure/reddit_client.py backend/app/services/hotpost/source_scope_candidate_collector.py backend/app/services/hotpost/hotpost_supply_contract.py
```

结果：
- 通过

### 受控真机验证

命令：

```bash
python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --max-candidates 8
```

结果：

```json
{"business-growth-ops": 5}
```

说明：
- 小流量单 scope collect 已能在新护栏下正常跑完
- 没再出现“整轮直接炸掉”的情况

## 当前结论

- Reddit 账号保护护栏已经正式进入主链，不再只靠人工感觉控制抓取节奏。
- 现在 collect 从“会炸”进一步推进到了“会主动收手”。
- 下一步该做的，不是再盲目加抓取，而是继续提高：
  - 在安全边界内的吞吐
  - `hot + breakdown` 的有效供给密度

## 下一步

1. 继续做 `collect` 安全模式和收割模式的分离
2. 在不增加账号风险的前提下，提高单轮可收割候选量
3. 优先恢复 `hot + breakdown` 的 lane mix，不再继续补 `signal`
