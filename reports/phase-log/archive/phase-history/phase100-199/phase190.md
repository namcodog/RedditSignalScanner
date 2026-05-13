# Phase 190

## 目标
- 用超管完成 `fk_discovered_to_pool` 外键移除迁移。
- 跑一次爆帖速递最小流程，验证中文输入可产出结果并写入 discovered_communities。

## 变更
- 无代码变更（仅执行迁移与验收）。

## 验证
- 执行命令：
  - `MIGRATION_DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_dev DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_dev alembic upgrade 20260202_000002`
  - `psql "postgresql://postgres@localhost:5432/reddit_signal_scanner_dev" -c "SELECT conname FROM pg_constraint WHERE conname='fk_discovered_to_pool';"`
  - `PYTHONPATH=backend python - <<'PY' ... HotpostService.search(query="最近 AI 工具领域有什么热门讨论？", mode="trending") ... PY`
  - `psql "postgresql://postgres@localhost:5432/reddit_signal_scanner_dev" -c "SELECT name, status, discovered_count, last_discovered_at FROM discovered_communities ORDER BY last_discovered_at DESC LIMIT 5;"`
- 结果：
  - 迁移成功，`fk_discovered_to_pool` 已移除。
  - 中文查询可返回结果（evidence_count=30，confidence=high，communities 包含 r/artificial / r/machinelearning）。
  - discovered_communities 最近记录已更新（r/artificial / r/machinelearning）。

## 结论
- 外键删除生效，爆帖速递中文查询与社区发现写入链路可用。

## 影响范围
- 仅 dev 数据库与本地 Redis。
