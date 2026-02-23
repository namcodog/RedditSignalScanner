# Phase 135 - PRD vs 运行入口 全量验收（依据 phase115）

日期：2026-01-21

## 目标
按 phase115 全量清单逐项核对运行入口与 PRD 对齐情况。

## 范围
- Makefile / makefiles/*
- docs/API-REFERENCE.md、docs/本地启动指南.md、docs/OPERATIONS.md
- frontend/src/router/index.tsx
- backend/app/core/celery_app.py
- 关键配置/脚本路径

## 验收结果
### 通过项（对齐）
- 系统运行入口（dev-golden-path / dev-backend / dev-frontend / celery-start / dev-celery-beat / restart / kill-ports）均存在
- 健康/诊断入口（/api/healthz、/api/tasks/diag、/api/diag/runtime、/api/tasks/stats、/openapi.json）在文档与代码中可见
- 数据模型入口（DB Atlas + current_schema.sql）存在
- 用户前端主要入口（/、/progress/:taskId、/report/:taskId、/decision-units、/login、/register）存在
- 用户链路 API 入口在 API-REFERENCE 中可检索到
- Admin API 入口在 API-REFERENCE 中可检索到
- 任务/调度入口与队列定义在 celery_app.py 中可检索到
- 抓取/清洗 SOP 与配置文件存在
- 语义库配置与脚本存在
- 导出与反馈入口在 API-REFERENCE 中可检索到
- 测试/演练入口（test-e2e/test-admin-e2e/test-contract/phase106 rehearsal matrix）存在

### 缺口/不一致
1) 前端洞察页路由
- phase115：`/insights/:taskId`
- 现状：`/insights`（见 `frontend/src/router/index.tsx`）

2) Admin 导入页路由
- phase115：`/admin/communities/import`
- 现状：路由未挂载（页面文件存在 `frontend/src/pages/admin/CommunityImport.tsx`）

3) 手动抓取入口
- phase115：`make crawl-seeds`
- 现状：`make crawl-seeds` 未在 `makefiles/dev.mk` 中找到（已有 `crawl-once` / `crawl-crossborder`）

## 结论
全量验收“基本对齐”，但仍有 3 处运行入口与清单不一致，需补齐或调整清单口径后才能判定完全通过。
