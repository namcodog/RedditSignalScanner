# Phase 256 - Round 3 社区治理根修（单一真相入口 + Dev 清理）

执行时间: 2026-03-13

## 1. 发现了什么

- Round 3 虽然已经把“社区治理链和语义链要说真话”这件事修到位了，但还有一个更底层的黑盒：
  - 现在真正生效的社区是谁？
  - 候选社区是谁？
  - 历史垃圾社区是谁？
  - 哪些只是以前导入过、后来又废弃了？
- 这套口径之前分散在：
  - `community_pool`
  - `discovered_communities`
  - `community_blacklist.yaml`
  - 历史导入和清理记录
- 结果就是：人难看懂，AI 更难稳定读懂。

## 2. 是否需要修复

- 需要，而且这次已经一起根修了。
- 这轮没有改数据库 schema，也没有新 migration。
- 但补了“单一真相入口”和“Dev 垃圾清理能力”，把社区治理从黑盒拉成了可读、可查、可清理的系统。

## 3. 精确修复方法

### 3.1 固定“真正生效社区”的唯一口径

- 新增 `CommunityGovernanceService`
- 统一定义：
  - 真正生效社区 = `community_pool` 中
    - `is_active = true`
    - `deleted_at is null`
    - `is_blacklisted = false`
- `discovered_communities` 只算候选池，不再和有效池混读。

### 3.2 新增治理快照和有效清单接口

- `GET /api/admin/communities/governance/summary`
  - 返回：
    - `effective_communities`
    - `candidate_communities`
    - `garbage_communities`
    - `anomalies`
- `GET /api/admin/communities/governance/effective`
  - 只返回真正起作用的社区清单

### 3.3 新增 Dev/Test 清理接口

- `POST /api/admin/communities/governance/cleanup-dev`
  - 支持 `dry_run`
  - 只允许 `reddit_signal_scanner_dev` / `reddit_signal_scanner_test`
  - 金库直接拒绝
- 清理规则：
  - 删除 `community_pool` 里的 inactive / soft-deleted / blacklisted 垃圾社区
  - 同步删除对应 `community_cache`
  - 删除 `discovered_communities` 里的 rejected / blacklisted / stale duplicate
  - 保留真正候选的 `pending`
  - `approved 但不在有效池` 只报异常，不自动删

### 3.4 Top1000 继续保持封口

- Top1000 仍然只允许 `deprecated_ignored`
- 不允许再从旧 Top1000 文件回流社区池

## 4. 验证结果

- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_governance_service.py tests/api/test_admin_community_pool.py -q`
  - `12 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/community/test_community_governance_service.py tests/services/community/test_community_pool_loader.py tests/services/community/test_community_pool_loader_full.py tests/services/community/test_candidate_vetting_service.py tests/services/community/test_evaluator_service.py tests/api/test_admin_community_pool.py -q`
  - `29 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `27 passed`

## 5. 这次执行的价值

- 这次不是再加一个管理页面，而是把“社区到底谁生效、谁候选、谁垃圾”这套口径正式钉死了。
- 用大白话说：
  - **以后你问系统‘现在真正起作用的社区有哪些’，它终于能给出一个唯一答案了。**
- 这也让后面的 AI 和人工运维不再需要从 4 份状态里自己猜。
