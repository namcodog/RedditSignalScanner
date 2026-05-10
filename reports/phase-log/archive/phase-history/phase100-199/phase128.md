# Phase 128 - 清理旧入口并统一 Makefile 口径

日期：2026-01-21

## 目标（说人话）
把 Makefile/脚本入口彻底收口：移除旧版入口，统一默认指向 Dev 库，避免再走旧口径。

## 做了什么
1) 清理旧入口
- 删除 `make crawl-seeds` / `make crawl-seeds-incremental`（旧版种子入口已移除，只保留现行入口）。

2) Makefile 口径统一到三库制
- 默认 `DB_NAME` 改为 `reddit_signal_scanner_dev`。
- `crawler-smart-status` 文案改为“本地 Dev 库”。
- `restore-db` 增加金库恢复保护：需 `ALLOW_GOLD_DB=1` 才允许写金库。
- 备份文件命名改为包含 DB 名，并同步最新备份到 `BACKUP_FILE`。

## 影响范围
- 旧入口不再可用，统一从现行入口执行。
- 默认数据库改为 Dev；金库必须显式放行。

## 验证
- 未运行测试（仅 Makefile/脚本入口调整）。

## 下一步
- 继续按需要梳理其它未在 Makefile/文档出现的脚本并归档。
