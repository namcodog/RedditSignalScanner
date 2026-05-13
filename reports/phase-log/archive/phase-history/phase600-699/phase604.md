# Phase 604 - pytest 误写 dev 根因修复与 live 复验

## 目标

- 查清为什么 `pytest` 之后 dev 库里会出现测试社区。
- 修掉这个根因。
- 再把 dev 社区盘恢复回来，并用同题 live 复验当前主链剩余问题。

## 发现

### 1. pytest 确实会误打到 dev，但根因不是 reset fixture

这次抓到的实锤是：

- `backend/tests/conftest.py` 顶部会先 import：
  - `app.db.database_guard`
- 但 Python 导入子模块前，会先执行：
  - `app.db.__init__`
- 旧的：
  - `backend/app/db/__init__.py`
  会在包导入阶段立刻 import `.session`
- `.session` 会在模块初始化时锁定：
  - `DATABASE_URL`

结果就是：

- pytest 虽然后面把 `DATABASE_URL` 设成 `*_test`
- 但 `SessionFactory` 早就已经用 dev DSN 初始化好了

这就是为什么前面看起来 guard 都在，dev 里却会出现：

- `r/daddit_ff669164`
- `r/parenting_a1f27ee9`
- `r/drifted_pool`

这类明显测试社区。

### 2. 修完后，dev 当前主问题已经变成“样本盘空”

修完根因并恢复社区盘后，readiness 当前是：

- `enabled_registry_count = 160`
- `approved_registry_count = 124`
- `active_runtime_count = 124`
- `recent_posts_count = 0`
- `recent_posts_with_semantic_count = 0`

这说明：

- 社区真相层已经回正
- 但样本盘/缓存盘当前还是空的

## 已完成修复

### 1. 修掉 `app.db.__init__` 的 eager import 根因

文件：

- `backend/app/db/__init__.py`

改动：

- 删除顶层直接 import `.session`
- 改成 lazy export
- 只有真正访问：
  - `SessionFactory`
  - `engine`
  - `get_session`
  时，才导入 `app.db.session`

这保证了：

- pytest 先把 `DATABASE_URL` 切到 `*_test`
- 再初始化 `SessionFactory`

### 2. 新增回归测试锁住这个根因

文件：

- `backend/tests/core/test_database_guard.py`

新增：

- `test_importing_database_guard_does_not_preload_session`

验证：

- import `app.db.database_guard` 后
- `app.db.session` 仍不应进入 `sys.modules`
- 真正访问 `app.db.SessionFactory` 时，才允许加载 session
- 且加载到的 DSN 必须是 `*_test`

### 3. 把 dev 社区盘恢复回正式状态

执行：

```bash
PYTHONPATH=backend ALLOW_GOLD_DB=1 .venv/bin/python \
  backend/scripts/community/restore_dev_community_truth_from_gold.py --write
```

结果：

- `pool_upserts = 228`
- `cache_upserts = 193`
- `deactivate_pool_count = 3`
- `deactivate_cache_count = 2`

恢复后 readiness：

- `enabled_registry_count = 160`
- `approved_registry_count = 124`
- `active_runtime_count = 124`

## 验证

### pytest 根因回归

```bash
cd backend && ../.venv/bin/python -m pytest \
  tests/core/test_database_guard.py \
  tests/core/test_community_reset_policy.py \
  tests/api/test_analyze.py -q
```

结果：

- `25 passed`

### 复查 dev 当前状态

- `community_pool.total = 231`
- `community_pool.active = 160`
- `community_cache.total = 195`
- `community_cache.active = 160`
- `community_registry.total = 230`
- `community_registry.enabled = 160`
- `posts_raw.total = 0`

### 同题 live 复验

query：

- `卖成人用品时，最卡下单成交的地方是什么？`

task：

- `d9e8e613-0487-4fa1-befc-a584fcb66390`

结果：

- task `completed`
- `analysis_id` 已生成
- `report_id` 已生成
- `facts_v2_quality.tier = C_scouting`
- `facts_v2_quality.flags = ['insufficient_samples']`
- 持久化 `InsightCard = 0`

这轮的关键点是：

- 报告仍可能有 `report_structured.decision_cards`
- 但正式 `insights` 已经不会再补 synthetic display cards

## 结论

这轮之后，两个关键结论已经坐实：

1. `pytest` 误写 dev 的根因已经找到并修掉
   不是 reset fixture 本身，而是 `app.db.__init__` 过早导入 `.session`。

2. 当前主链失败已经更诚实
   现在同题 live 继续停在 `C_scouting`，主因是：
   - `insufficient_samples`
   - 当前 dev 样本盘为空

而不是：

- DB 真相层漂
- synthetic display cards 假装有洞察

## 下一步

1. 针对主链再补一层前置判断：
   - 区分“社区盘就绪”与“样本盘就绪”
2. 给 dev 拉回最小可用样本盘，再跑 live
3. 如果样本盘恢复后仍只是 `C_scouting`，再直接处理分析链和证据链
