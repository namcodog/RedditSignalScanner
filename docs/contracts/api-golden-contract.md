# API 门牌契约（冻结版）

日期：2025-12-17

## 一句话

对外 **只认 `/api`**，不提供 `/api/v1` 这种第二套门牌（先跑稳再演进）。

## 为什么要这么干（大白话）

- 只有一个门牌：调用方永远不会迷路。
- 先跑稳再升级：以后要做 `/api/v1`，也必须是“新增不破坏”，而不是把现有 `/api` 改掉。

## 这份契约怎么被“冻结”

- 后端有一条契约测试：`backend/tests/api/test_api_contract.py`
  - 会检查 OpenAPI 里存在 `/api/analyze` 等主线端点
  - 并明确要求 **不能出现 `/api/v1` 开头的路径**

## 当前主线端点（不列全，只列黄金链路）

- `POST /api/analyze`：创建分析任务（黄金入口）
- `GET  /api/status/{task_id}`：查询任务状态
- `GET  /api/analyze/stream/{task_id}`：SSE 进度流
- `GET  /api/report/{task_id}`：获取报告

> 备注：auth/admin/metrics 等辅助端点不在“黄金链路”里，但仍然沿用 `/api` 前缀。

