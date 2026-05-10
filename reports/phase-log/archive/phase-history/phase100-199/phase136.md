# Phase 136 - 补入口并复检

日期：2026-01-21

## 目标
补齐缺失入口并复检 phase115 发现的不一致项。

## 变更
- 新增洞察任务路由：`/insights/:taskId`
- 新增 Admin 导入路由：`/admin/communities/import`
- 新增运行入口：`make crawl-seeds`（alias 到 `crawl-once`，默认 `SCOPE=T1`）

## 复检
- `frontend/src/router/index.tsx` 已包含 `/insights/:taskId` 与 `communities/import`
- `makefiles/dev.mk` 已包含 `crawl-seeds`

## 结论
入口缺口已补齐，可进行全量复检确认。
