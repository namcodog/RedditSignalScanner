# Phase 750 - 小程序产品态基线 checkpoint

## 发现

- 主仓库仍是大脏工作区，直接在主仓库打 tag 不能保护未跟踪的小程序状态。
- `hotpost-mini/hotpost-mini-app` 本身是独立 git 仓库，且已有 `product-baseline.cjs` 基线机制，适合做小程序产品态 checkpoint。

## 执行

- 在 `hotpost-mini/hotpost-mini-app` 执行 `npm run baseline:promote`。
- 该命令先执行 `npm run build:weapp`，构建通过后提交当前小程序状态并创建 baseline tag。

## 基线

- baseline tag: `baseline/product-state-2026-04-10-133351`
- baseline commit: `dd4d736`
- release: `release-3322c8490398`
- card_count: `125`
- feed_contract: `30/30`

## 恢复方式

在小程序目录执行：

```bash
cd /Users/hujia/Desktop/RedditSignalScanner/hotpost-mini/hotpost-mini-app
npm run baseline:restore
```

如果要同时清掉未跟踪文件：

```bash
npm run baseline:restore:hard
```

## 验证

- `npm run build:weapp` -> passed。
- `npm run baseline:status` -> `matches_baseline: yes`, `worktree_dirty: no`。
- `PYTHONPATH=backend python backend/scripts/hotpost/check_mini_release_sync.py` -> backend snapshot、miniRelease、miniFavorites、cloud_db meta 均为 `feed_contract=30/30 status=ok`。

## 结论

- 当前小程序产品态已经有可回滚基准节点。
- 后续如果 UI、云函数、登录、收藏或 release 读取改坏，可以先回到该 baseline，再继续单变量排障。
