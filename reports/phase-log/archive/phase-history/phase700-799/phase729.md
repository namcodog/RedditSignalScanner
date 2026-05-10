# Phase 729

## 本轮目标

先把 `hot` 线稳住，再做一次完整审计，确认 `爆贴热点` 不是因为收割不够，而是因为供给路由和判定规则是否真正落地。

## 发现

- 问题不是 collect 不肯等，而是 `hot` 候选入口太脏、judge 太粗。
- 修完脏入口并重跑 `ai-automation / ecommerce-sellers` collect 后：
  - `candidate_total = 69`
  - `listing_total = 14`
  - `runtime_hot_total = 2`
  - `published_hot_total = 3`
- 新的运行时 `hot` 只剩两条：
  - `cand-ai-automation-1sftdkl` / `r/OpenAI`
  - `cand-business-growth-ops-1sbr4k1` / `r/SEO`
- 旧的噪音热点已经被冲掉：
  - `CleaningTips / Frugal / EntrepreneurRideAlong` 不再出现在 `runtime_hot`

## 实现

### 1. `hot` 供给合同继续 YAML 化

文件：
- `backend/config/hotpost_supply_discovery_v2.yaml`
- `backend/app/services/hotpost/hotpost_supply_contract.py`

新增：
- `min_collective_comments`
- `direct_question_markers`

### 2. `hot` judge 收紧后补一刀“放回真实热点”

文件：
- `backend/app/services/hotpost/card_lane_policy.py`

改动：
- 直接问法 + 求助意图，继续挡在 `signal`
- 纯高热围观 / 情绪 / 实操分享，继续挡在 `signal`
- 允许两类真正像 `hot` 的帖子回来：
  - 高热路线争论帖，即便意图标签有噪音
  - 群体短句接力的集体反应帖，不再只认超长评论

### 3. 全包审计

文件：
- `backend/app/services/hotpost/hot_lane_audit.py`
- `backend/scripts/hotpost/audit_hot_lane.py`
- `reports/evals/hot_lane_audit_v1.json`
- `reports/evals/hot_lane_audit_v1.md`

## 验证

- `pytest backend/tests/services/hotpost/test_card_lane_policy.py -q`
  - `10 passed`
- `python -m py_compile backend/app/services/hotpost/card_lane_policy.py backend/app/services/hotpost/hotpost_supply_contract.py`
  - 通过
- `python backend/scripts/hotpost/daily_collect.py --scope ai-automation --max-candidates 24`
  - `{"ai-automation": 23}`
- `python backend/scripts/hotpost/daily_collect.py --scope ecommerce-sellers --max-candidates 24`
  - `{"ecommerce-sellers": 22}`
- `python backend/scripts/hotpost/audit_hot_lane.py`
  - 产出最新审计文件

## 结论

- `hot` 线现在已经从“脏热点误入”收成“少量但站得住的热点候选”。
- 这次证明：
  - 问题不是 Reddit 没热点
  - 也不是 collect 没等够
  - 而是 `hot` 的入口和判定之前没把你的定义翻译成机器规则
- 当前 `hot` 已经不乱，但还没厚；下一步该补的是 `hot` 专用供给密度，不是再放松门禁。
