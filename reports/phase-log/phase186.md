# Phase 186 - 解除 discovered_communities 外键约束

日期：2026-02-01

## 本阶段目标
- 让 discovered_communities 成为独立候选库，不依赖 community_pool。

## 主要改动
- 新增迁移移除外键：
  - `backend/alembic/versions/20260202_000002_drop_discovered_fk.py`
- hotpost 写入候选库：仅规范化 + 去重，不再依赖 community_pool：
  - `backend/app/services/hotpost/repository.py`
- 更新测试：
  - `backend/tests/services/hotpost/test_hotpost_repository.py`

## 测试
```bash
DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test \
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_repository.py -q
```

结果：1 passed（含 pytest 警告）

## 备注
- 生产/开发库需执行迁移：`alembic upgrade 20260202_000002`（或指定 heads，注意多头分支）。
