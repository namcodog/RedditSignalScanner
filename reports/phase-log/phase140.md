# Phase 140 - 口径复核引用修正 + Week2 验收阻塞记录

日期：2026-01-21

## 目标
1) 复核归档文档引用，确保现行口径不再指向旧路径。  
2) 启动测试库环境以执行 Week2 验收。

## 口径复核与修正
- 更新 `makefiles/tools.mk` 中 MCP 指南路径，改为 `docs/archive/MCP-SETUP-GUIDE.md`。
- 更新 `.specify` 中对旧文档的引用路径：
  - `docs/2025-11-主业务线说明书.md` → `docs/archive/2025-11-主业务线说明书.md`
  - `docs/分析算法设计详解.md` → `docs/archive/分析算法设计详解.md`
  - `docs/annotation-guide.md` → `docs/archive/annotation-guide.md`
- 当前仅剩历史报告/phase-log 里保留旧路径引用（用于追溯，不做修改）。

## Week2 验收尝试（测试库）
- 使用 `DATABASE_URL` 自动派生测试库名：`reddit_signal_scanner_dev_test`
- 执行 `make dev-golden-path` 失败：数据库不存在
- 报错：`asyncpg.exceptions.InvalidCatalogNameError: database \"reddit_signal_scanner_dev_test\" does not exist`

## 结论
Week2 验收尚未完成，阻塞原因是测试库未创建。

## 待确认
- 是否允许创建测试库 `reddit_signal_scanner_dev_test` 后继续验收？
- 或提供指定的测试库 DSN。
