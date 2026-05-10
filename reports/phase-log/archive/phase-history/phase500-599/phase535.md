# Phase 535 - Dev 社区层按金库口径恢复

## 背景

- `phase534` 已确认：
  - 金库当前真实运行口径仍是 `community_pool.categories`
  - Dev 的正式社区盘、抓取盘、分类盘已明显漂移
- 因此这轮不继续空谈新真相源切换，而是先做：
  - 金库只读快照
  - Dev 定向恢复
  - 再把恢复后的真实口径回灌到新真相源

## 本轮执行

### 1. 新增受控恢复服务

新增：

- [gold_dev_community_restore_models.py](../../backend/app/services/community/gold_dev_community_restore_models.py)
- [gold_dev_community_restore_service.py](../../backend/app/services/community/gold_dev_community_restore_service.py)
- [restore_dev_community_truth_from_gold.py](../../backend/scripts/community/restore_dev_community_truth_from_gold.py)

设计原则：

- 金库只读
- Dev 可写
- 先 `dry-run`
- 再 `--write`
- 不做全库复制，只恢复社区层正式资产

恢复内容：

- `community_pool`
- `community_cache`
- `community_category_map`
- 同时退役挂在非有效社区池上的 truth-source 遗留行

### 2. 补齐测试

新增测试：

- [test_gold_dev_community_restore_service.py](../../backend/tests/services/community/test_gold_dev_community_restore_service.py)

覆盖点：

- 金库快照恢复到 Dev
- Dev-only 社区池 / 缓存停用
- truth-source 遗留行退役
- `dry-run` 不落库

验证：

- `pytest backend/tests/services/community/test_gold_dev_community_restore_service.py -q`
- `2 passed`

### 3. 执行真实恢复

先跑 dry-run：

- [gold_dev_restore_1774633411.json](../../backend/reports/local-acceptance/gold_dev_restore_1774633411.json)

关键预演结果：

- `pool_upserts = 228`
- `cache_upserts = 193`
- `pool_deactivated = 280`
- `cache_deactivated = 74`

然后真实写入：

- [gold_dev_restore_1774633427.json](../../backend/reports/local-acceptance/gold_dev_restore_1774633427.json)

补一刀 truth-source 退役清理：

- [gold_dev_restore_1774633856.json](../../backend/reports/local-acceptance/gold_dev_restore_1774633856.json)
- [gold_dev_restore_1774633974.json](../../backend/reports/local-acceptance/gold_dev_restore_1774633974.json)

### 4. 回灌新真相源

执行：

- `PYTHONPATH=backend python3 backend/scripts/community/reconcile_truth_sources.py --json-only`

结果：

- `scanned = 160`
- `synced = 160`
- `skipped = 0`

## 当前结果

### 金库（对照）

- `community_pool.total = 228`
- `community_pool.effective = 160`
- `community_pool.with_categories = 228`
- `community_cache.total = 193`
- `community_cache.active = 160`

### Dev（恢复后）

- `community_pool.total = 508`
- `community_pool.effective = 160`
- `community_pool.with_categories = 228`
- `community_cache.total = 267`
- `community_cache.active = 160`
- `community_category_map.rows = 228`

### Dev 新真相源（恢复后）

- `community_registry.total = 233`
- `community_registry.enabled = 160`
- `community_runtime_state.total = 233`
- `community_runtime_state.enabled = 160`
- `community_domain_membership.total = 160`
- `community_domain_membership.current = 160`
- `community_governance_decision.total = 160`
- `community_governance_decision.current = 160`

## 结论

### 1. 正式运行盘已回正

Dev 当前真正参与运行的社区层已经与金库对齐：

- 有效社区盘 `160`
- 活跃抓取盘 `160`
- 分类口径已回到 `228` 条正式社区

### 2. 新真相源已吃到恢复后的正式盘

现在不是只有旧表恢复了，而是：

- `registry.enabled = 160`
- `runtime.enabled = 160`
- `membership.current = 160`
- `governance.current = 160`

这说明“恢复后的正式盘”已经开始进入新真相源。

### 3. 还没做物理压缩

当前仍保留了大量已停用历史行：

- `community_pool.total = 508`
- `community_cache.total = 267`
- `community_registry.total = 233`

这不是运行时污染，因为有效/启用态已经对齐。

但它仍然说明：

- Dev 已完成“逻辑收口”
- 还没完成“物理压缩/彻底瘦身”

## 下一步

1. 做 Dev 社区层物理压缩方案：
   - 把已停用的 `community_pool / community_cache / community_registry / runtime` 历史行收成可归档、可删除、可重建的方案
2. 继续把主链读路径切到新真相源
3. 再恢复横向 live 验收，而不是反过来

## 本轮价值

- 这轮第一次把“Dev 社区层漂移”从抽象问题变成了可执行恢复流程。
- 也把数据库状态分成了两层：
  - 运行时是否干净
  - 物理存量是否瘦身
- 到这一步，Dev 已不再是“盲盒库”，而是重新有了可信的正式社区盘。
