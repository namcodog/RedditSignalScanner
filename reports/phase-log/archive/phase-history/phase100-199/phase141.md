# Phase 141 - Week2 验收启动失败（测试库权限不足）

日期：2026-01-22

## 目标
在测试库 `reddit_signal_scanner_test` 上启动黄金路径，为 Week2 验收做准备。

## 执行记录
- 使用 `DATABASE_URL=.../reddit_signal_scanner_test` 启动 `make dev-golden-path`
- 迁移成功、后端启动成功
- 步骤“创建测试用户和任务”失败：

```
permission denied for table users
```

## 结论
测试库中应用账号（rss_app）对 `users` 表权限不足，导致无法 seed 用户/任务。
Week2 验收未进入执行阶段。

## 待确认
需要明确测试库的权限策略：
1) 允许在测试库使用 `postgres` 用户运行（DATABASE_URL 改为 postgres 用户）
2) 或为 `rss_app` 在测试库授予必要权限（users/tasks/analyses 等）

确认后才能继续 Week2 验收。
