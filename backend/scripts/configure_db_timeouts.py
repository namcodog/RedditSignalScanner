#!/usr/bin/env python3
from __future__ import annotations

"""
一次性配置 PostgreSQL 的超时“总闸门”，防止僵尸连接无限增长。

作用范围：当前 app 使用的数据库（默认 reddit_signal_scanner_dev）。

推荐配置：
  - idle_in_transaction_session_timeout = 60s  # 事务闲置超过 60 秒自动回滚 + 断开
  - statement_timeout                  = 30s  # 单条语句最长 30 秒
  - lock_timeout                       = 5s   # 等锁超过 5 秒直接放弃

用法：
  1）只打印推荐 SQL（不会真正改数据库）：
        cd backend
        python -u scripts/configure_db_timeouts.py

  2）尝试直接在当前数据库上执行（需要有 ALTER DATABASE 权限）：
        cd backend
        python -u scripts/configure_db_timeouts.py --apply

  3）如果 --apply 失败，可以把输出的 SQL 复制到 psql 里手动执行：
        psql -U postgres -d reddit_signal_scanner_dev
        -- 粘贴脚本打印出来的 ALTER DATABASE 语句
"""

import argparse

from sqlalchemy import text

from app.db.session import engine, DATABASE_URL


def _build_sql(db_name: str) -> list[str]:
    return [
        f"ALTER DATABASE {db_name} SET idle_in_transaction_session_timeout = '60s';",
        f"ALTER DATABASE {db_name} SET statement_timeout = '30s';",
        f"ALTER DATABASE {db_name} SET lock_timeout = '5s';",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure PostgreSQL timeouts to auto-clean idle transactions."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="直接在当前数据库执行 ALTER DATABASE 语句（需有权限）。",
    )
    args = parser.parse_args()

    # 解析当前数据库名
    from urllib.parse import urlparse

    url = DATABASE_URL.replace("+asyncpg", "")
    parsed = urlparse(url)
    db_name = (parsed.path or "").lstrip("/") or ""

    if not db_name:
        print("❌ 无法从 DATABASE_URL 解析数据库名，请检查配置。")
        return 1

    stmts = _build_sql(db_name)

    print("==========================================")
    print("PostgreSQL 超时配置（推荐值）")
    print("目标数据库:", db_name)
    print("==========================================")
    print()
    for s in stmts:
        print(s)
    print()

    if not args.apply:
        print("💡 说明：当前仅打印推荐 SQL，并未真正修改数据库。")
        print("   如需直接应用，请使用：python -u scripts/configure_db_timeouts.py --apply")
        return 0

    # 尝试直接执行 ALTER DATABASE
    print("🔧 正在尝试在数据库上应用上述配置（需要 ALTER DATABASE 权限）...")
    try:
        # 使用同步引擎执行 DDL
        sync_engine = engine.sync_engine
        with sync_engine.begin() as conn:
            for stmt in stmts:
                conn.execute(text(stmt))
        print("✅ 已成功应用超时配置。新的连接将自动继承这些设置。")
        return 0
    except Exception as exc:  # pragma: no cover - 依赖外部数据库权限
        print("⚠️ 无法自动应用配置，请手动在 psql 中执行上面的 SQL。")
        print(f"   具体错误: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
