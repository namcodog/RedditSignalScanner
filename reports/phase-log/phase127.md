# Phase 127 - 程序化三库制收口（默认 Dev + 金库拦截）

日期：2026-01-21

## 目标（说人话）
把“默认写库=Dev、金库只对照”的口径落到代码里，避免任何人一不小心写进金库。

## 做了什么
1) 默认数据库切到 Dev
- `app/core/config.py`、`app/db/session.py` 的默认库名改为 `reddit_signal_scanner_dev`。
- `backend/.env.example`、`backend/alembic.ini` 默认库同步为 Dev。

2) 增加金库保护闸
- 新增 `app/db/database_guard.py`：非生产环境默认禁止连金库。
- 通过 `ALLOW_GOLD_DB=1` 可显式放行对照金库。
- `app/db/session.py` 启动时自动触发校验。

3) 脚本口径同步
- `backend/monitor_db_connections.sh` 默认监控 Dev（支持 `DB_NAME` 覆盖）。
- `backend/scripts/configure_db_timeouts.py`、`backend/scripts/smart_crawler_workflow.py` 提示口径切到 Dev。
- `backend/analyze_test_results.py`、`backend/scripts/analyze_community_value.py` 默认库切到 Dev。

4) 文档同步补充
- `docs/DATABASE_CONFIGURATION.md`、`docs/sop/数据库使用规范_v2_全景版.md` 补充 `ALLOW_GOLD_DB` 说明。
- `backend/alembic/README.md` 迁移示例改为 Dev。

5) 测试先行
- 新增 `backend/tests/core/test_database_guard.py`，覆盖金库拦截/放行场景。
- 更新 `backend/tests/models/test_database_indexes.py` 的默认库断言。

## 测试
```bash
SKIP_DB_RESET=1 pytest backend/tests/core/test_database_guard.py \
  backend/tests/models/test_database_indexes.py::test_settings_default_database_name -q
```
结果：✅ 5 passed（有 1 条 pytest 配置警告，不影响结果）

## 影响范围
- 默认写库改为 Dev；金库需显式放行。
- 不涉及业务逻辑改动，仅口径与安全护栏。

## 下一步
- 若需要，把更多脚本入口统一接入 `DATABASE_URL` + 保护闸。
