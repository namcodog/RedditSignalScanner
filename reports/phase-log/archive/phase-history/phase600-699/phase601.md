# Phase 601 - live 主链前置筛查与首轮真验收归因

## 目标

- 按新的主链计划先做 live 前置筛查，不再盲跑。
- 用当前已收好的社区真相源与语义账本，真实跑一次 open-question live。
- 把结果明确归因到数据、分析或输出，不继续把问题混在一起。

## 发现

### 1. dev 的 truth-source 在跑 live 前一度被清空

前置筛查时发现：

- `community_registry = 0`
- `community_runtime_state = 0`
- `community_domain_membership = 0`
- `community_governance_decision = 0`

但旧投影层还有残留：

- `community_pool.active = 47`
- `community_cache.active = 1`

这说明当时主链虽然能“启动”，但真相源已经空了，直接跑 live 没有意义。

### 2. 已按既有恢复链把 dev 社区真相层拉回来了

使用既有恢复脚本与 reconcile 脚本：

- `backend/scripts/community/restore_dev_community_truth_from_gold.py`
- `backend/scripts/community/reconcile_truth_sources.py`

恢复后 readiness 关键指标变成：

- `enabled_registry_count = 160`
- `registry_with_current_membership_count = 124`
- `approved_registry_count = 124`
- `active_runtime_count = 124`

这说明：

- 社区真相源已经重新接回主链
- 但 readiness 还不是满格，不能默认期待 `A_full`

### 3. 这次 live 不是脚本挂死，而是真结果只到 `C_scouting`

本次任务：

- `task_id = 131dd307-788a-4e96-af6f-9dd398819433`
- 用户：`test@test.com`
- 查询：`卖成人用品时，最卡下单成交的地方是什么？`

真实状态接口返回：

- `status = completed`
- `blocked_reason = insufficient_samples`
- `next_action = auto_rerun_scheduled`
- `attempt = 3 / max_attempts = 3`

说明：

- 主任务很快完成
- 自动重跑也跑满了
- 但还是没有升到 `A_full`

### 4. 当前主链仍存在输出层 synthetic display cards

analysis worker 日志明确出现：

- `No persisted insight cards for task ...; runtime fallback will serve synthetic display cards`

这说明这次 live 里，输出层仍然存在 synthetic display cards 介入。

这和我们当前“不写兜底代码、不靠假内容遮丑”的原则冲突。

## 归因结论

这次 live 问题已经可以明确拆成两层：

1. **数据层问题**

- readiness 只到 `124 / 160`
- 最近窗口样本偏薄
- `recent_posts_with_semantic_count = 0`
- 当前 query 对应的数据盘还不足以支撑 `A_full`

2. **输出层问题**

- 当前报告虽然能生成
- 但仍会退回 synthetic display cards
- 导致输出里出现 `r/insight / r/insight_2 / r/insight_3` 这类显然不该进入正式报告的占位内容

所以这次结果不能再归因成“脚本不稳定”。

更准确的说法是：

- **主链已能跑通**
- **但当前 query 只达到 `C_scouting`**
- **根因是样本不足 + 输出层仍有 synthetic fallback**

## 验证

### readiness 前置筛查

```bash
cd backend && ../.venv/bin/python - <<'PY'
import asyncio, json
from app.db.session import SessionFactory
from app.services.community.truth_source_readiness_service import read_truth_source_readiness_snapshot
async def main():
    async with SessionFactory() as session:
        snap = await read_truth_source_readiness_snapshot(session, lookback_days=90)
        print(json.dumps(snap.as_dict(), ensure_ascii=False, indent=2))
asyncio.run(main())
PY
```

### 恢复 dev 社区真相层

```bash
PYTHONPATH=backend ALLOW_GOLD_DB=1 .venv/bin/python backend/scripts/community/restore_dev_community_truth_from_gold.py --write
PYTHONPATH=backend .venv/bin/python backend/scripts/community/reconcile_truth_sources.py --json-only
```

### live 验收

```bash
cd backend && PYTHONPATH=. ../.venv/bin/python scripts/acceptance/run_open_question_live_acceptance.py \
  --suite final \
  --product-description '卖成人用品时，最卡下单成交的地方是什么？' \
  --required-tier A_full
```

### 任务真实状态核验

```bash
python - <<'PY'
import requests
base='http://127.0.0.1:8016'
login=requests.post(base+'/api/auth/login', json={'email':'test@test.com','password':'Test123!'}, timeout=15)
token=login.json()['access_token']
headers={'Authorization':f'Bearer {token}'}
for path in ['/api/status/131dd307-788a-4e96-af6f-9dd398819433','/api/report/131dd307-788a-4e96-af6f-9dd398819433']:
    r=requests.get(base+path, headers=headers, timeout=20)
    print(path, r.status_code, r.text[:1200])
PY
```

## 结论

这轮最大的价值不是拿到了 `A_full`，而是把问题重新拉直了：

- 社区真相源已经真实接回主链
- 语义账本也已经接入主链消费侧
- 这次 live 没提分，不再能怪到 DB/语义底盘
- 当前主因已经收窄成：
  - 样本与 readiness 不足
  - 输出层 synthetic display cards 仍在污染正式报告

## 下一步

1. 先处理输出层 synthetic display cards，禁止它再进入正式 live 报告。
2. 把 live 前置筛查沉淀成固定入口，先筛 readiness，再决定跑不跑 `A_full`。
3. 再次跑主链 live 验收，把剩余问题继续压缩到“数据不足”或“分析不到位”，不让输出兜底继续掩盖问题。
