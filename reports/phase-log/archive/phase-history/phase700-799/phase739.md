# Phase 739 - collect 安全/收割双模式落地验证

## 发现了什么

- 当前主问题已经不是“collect 有没有护栏”，而是“护栏有了之后，怎么把收割和保号分开”。
- 原来 `daily_collect.py` 只有一套节奏，导致：
  - 想验证时太重
  - 想收割时又不够稳
- 同时这轮也验证了一个更硬的事实：
  - `safe/harvest` 模式已经能跑出差异
  - 但 `harvest` 之后，`hot` 和 `breakdown` 供给仍然没有自然变厚

## 是否需要修复

- 这轮模式拆分已经修完。
- 但 lane 供给问题没有一起自动解决：
  - `hot` 还是旧的 3 条 runtime 候选
  - `breakdown` 还是 `0`

## 精确修复方法

### 1. collect 双模式

文件：
- `backend/config/hotpost_supply_discovery_v2.yaml`
- `backend/app/services/hotpost/hotpost_supply_contract.py`
- `backend/app/services/hotpost/source_scope_candidate_collector.py`
- `backend/scripts/hotpost/daily_collect.py`

已落地：
- 新增 `collect_profiles`
  - `safe`
  - `harvest`
- `collect_scope_candidates` 支持 `mode`
- `daily_collect.py` 支持：

```bash
python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --mode safe
python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --mode harvest
```

### 2. safe / harvest 差异

当前配置差异：
- `safe`
  - `max_candidates_per_scope: 12`
  - `comments_fetch_limit: 3`
  - `api_max_concurrency: 3`
  - `spec_batch_size: 4`
  - `max_search_specs_per_scope: 60`
  - `max_listing_specs_per_scope: 24`
  - `stop_comment_fetch_below_remaining: 24`
- `harvest`
  - `max_candidates_per_scope: 24`
  - `comments_fetch_limit: 5`
  - `api_max_concurrency: 6`
  - `spec_batch_size: 8`
  - `max_search_specs_per_scope: 120`
  - `max_listing_specs_per_scope: 36`
  - `stop_comment_fetch_below_remaining: 18`

## 验证结果

### 定向测试

命令：

```bash
cd backend && pytest tests/services/hotpost/test_source_scope_candidate_collector.py -q
```

结果：
- `9 passed`

新增覆盖：
- `safe` 模式会读取更保守的 collect profile
- 低配额时会跳过评论补抓

### 受控真机验证

命令：

```bash
python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --mode safe
python backend/scripts/hotpost/daily_collect.py --scope business-growth-ops --mode harvest
```

结果：
- `safe -> 4`
- `harvest -> 8`

这说明：
- 双模式不是假动作
- `safe` 真在保守收割
- `harvest` 真在加大进口

## harvest 后的 lane 盘子

### hot 审计

命令：

```bash
python backend/scripts/hotpost/audit_hot_lane.py
```

结果：
- `candidate_total = 31`
- `listing_total = 14`
- `runtime_hot_total = 3`
- `published_hot_total = 6`

当前 runtime hot 仍然只有这 3 条：
- `cand-ai-automation-1sftdkl`
- `cand-ai-automation-1sb5616`
- `cand-ai-automation-1sd78l0`

### breakdown materialize

命令：

```bash
python backend/scripts/hotpost/materialize_breakdown_drafts.py
```

结果：

```json
{"count": 0, "materialized": 0, "skipped_existing": 0, "failed": 0, "items": []}
```

说明：
- `harvest` 并没有顺手把 `breakdown` 供给恢复起来

## 当前结论

- collect 已经正式分成：
  - `safe`
  - `harvest`
- 账号保护和收割目标不再混成一套参数
- 但这轮也把一个更重要的事实钉死了：
  - **现在 lane 失衡已经不是 collect 模式问题**
  - 而是 `hot + breakdown` 供给本身还不够厚

## 下一步

1. 继续保留 `safe / harvest` 这套 collect 分层
2. 停止再纠缠 collect 是否“还不够多”
3. 直接转去补：
   - `hot` 的争论型供给面
   - `breakdown` 的 suggestion 供给面
