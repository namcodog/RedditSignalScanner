# Phase 129 - 入口口径验证 + 数据库安全核查

日期：2026-01-21

## 目标（说人话）
确认数据库数据未受影响，并验证入口/口径统一且可运行。

## 做了什么
1) 只读核查数据库安全
- 查看三库大小（gold/dev/test）
- 查看关键表计数与最新时间
- 查看当前连接状态

2) 入口口径核对
- Makefile 默认库名为 Dev（`DB_NAME=reddit_signal_scanner_dev`）
- 金库恢复保护：需要 `ALLOW_GOLD_DB=1`
- 旧入口 `crawl-seeds` / `crawl-seeds-incremental` 已移除

3) 最小化测试验证
- 验证金库拦截与默认库名

## 结果（只读核查）
- 数据库大小：
  - reddit_signal_scanner: 6116 MB
  - reddit_signal_scanner_dev: 6116 MB
  - reddit_signal_scanner_test: 18 MB
- 关键表计数（dev / gold 一致）：
  - community_pool: 228
  - posts_raw: 195197
  - comments: 2063820
  - tasks: 17
  - posts_raw 最新时间：2025-12-21 18:03:53+08
- 当前连接：dev/gold 均无活跃连接

## 测试
```bash
SKIP_DB_RESET=1 pytest backend/tests/core/test_database_guard.py \
  backend/tests/models/test_database_indexes.py::test_settings_default_database_name -q
```
结果：✅ 5 passed（1 条 pytest 配置警告）

## 影响范围
- 仅验证与只读核查，无数据写入。

## 下一步
- 如需更严格的“未改动证明”，可补一次 gold 库的表级校验或校验和快照。
