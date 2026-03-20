# Phase 269 - Round 5 第二阶段：高风险导入/恢复脚本治理

## 本轮目标

把 3 个高风险导入/恢复脚本从“直接写库、默认可执行、会把 ghost 社区拉回池子”的状态，收口成：

- 只允许 Dev/Test 执行
- 默认 dry-run
- ghost 社区默认不恢复
- 脚本状态和执行意图说真话

## 涉及文件

- `backend/scripts/import/import_166_crossborder_communities.py`
- `backend/scripts/import/import_hybrid_scores_to_pool.py`
- `backend/scripts/import/restore_pool_hybrid.py`
- `backend/scripts/import_safety.py`
- `backend/tests/scripts/test_import_script_safety.py`

## 发现了什么

- 3 个脚本都直接走 `SessionFactory()` 写库，没有统一的数据库身份护栏。
- 这意味着它们理论上可以直接改 `reddit_signal_scanner`，和三库规则冲突。
- 3 个脚本原来都不是默认 dry-run，执行意图不够克制。
- `restore_pool_hybrid.py` 会根据 `posts_raw` 把 ghost 社区重新恢复进 `community_pool/community_cache`，直接冲撞 Round 3 社区治理口径。

## 是否需要修复

需要，而且这轮已经修完。

## 精确修复方法

### 1. 抽统一脚本护栏

新增 `backend/scripts/import_safety.py`：

- `ensure_dev_or_test_database()`
  - 复用现有数据库目标校验
  - 再额外收口：只允许 `reddit_signal_scanner_dev` / `reddit_signal_scanner_test`
- `add_execute_flag()`
  - 给脚本统一补 `--execute`
  - 不传时默认 dry-run
- `is_dry_run()`
  - 统一 dry-run 判断

### 2. 两个导入脚本统一默认 dry-run

`import_166_crossborder_communities.py` 和 `import_hybrid_scores_to_pool.py` 统一改成：

- `build_parser()`
- `_run_import(..., execute: bool)`
- 默认 dry-run
- 只有显式 `--execute` 才 commit
- dry-run 下只统计 `inserted / updated / skipped`，最后 rollback

### 3. 恢复脚本默认禁止 ghost recovery

`restore_pool_hybrid.py` 新增：

- `--execute`
- `--allow-ghost-recovery`

新默认行为：

- dry-run 默认开启
- `allow_ghost_recovery=False` 默认开启
- CSV 配置里的社区可以正常参与 restore 统计
- `posts_raw` 扫出来但不在 CSV 里的 ghost 社区，默认只计入 `ghosts_blocked`
- 只有显式传 `--allow-ghost-recovery` 才允许恢复

## 验证

### 定向脚本护栏测试

命令：

```bash
cd backend && SKIP_DB_RESET=1 python -m pytest tests/scripts/test_import_script_safety.py -q
```

结果：

- `6 passed`

覆盖点：

- 金库写入被拒绝
- Dev/Test 允许执行
- 3 个脚本默认都是 dry-run
- `restore_pool_hybrid.py` 默认禁止 ghost recovery

### 质量门禁

命令：

```bash
SKIP_DB_RESET=1 make test-quality-gate
```

结果：

- `27 passed`

## 统一口径

Round 5 第二阶段解决的是：

- 高风险导入/恢复脚本会把“危险写入”伪装成普通操作

修完后统一口径变成：

- 不是 Dev/Test，就别写
- 不显式 `--execute`，就只做 dry-run
- ghost 社区不再默认恢复
- 脚本的“看一眼”和“真执行”是两种清楚状态

## 下一步

Round 5 还剩最后一段：

- 收口旧版报告路由：`backend/app/api/routes/reports.py`

目标：

- 不再让新旧两套报告路由继续漂移
- 让报告 API 只保留一个真相实现

## 价值

这轮的价值不是加功能，而是把最危险的几支脚本收成“默认保守、显式执行、默认不污染社区池”。

一句大白话：

- 这些脚本现在不会再一上来就改库，也不会默认把 ghost 社区偷偷拉回来了。
