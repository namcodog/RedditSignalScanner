# Phase 182 - Hotpost 后端落地（词库+接口+入库）

日期：2026-01-28

## 本阶段目标
- 按《Reddit爆帖速递_产品模块文档》落地后端核心骨架（词库、规则、入库、API）。

## 主要改动
- 新增词库加载与轻量规则：`backend/app/services/hotpost/keywords.py`、`backend/app/services/hotpost/rules.py`
- 新增 hotpost schemas：`backend/app/schemas/hotpost.py`（含 search/deepdive 结构）
- 新增 hotpost 服务与入库逻辑：`backend/app/services/hotpost/service.py`、`backend/app/services/hotpost/repository.py`
- 新增 DB 模型：`backend/app/models/hotpost_query.py`、`backend/app/models/hotpost_query_evidence_map.py`
- 新增迁移：`backend/alembic/versions/20260128_000001_add_hotpost_tables.py`
- 新增 API 路由：`backend/app/api/v1/endpoints/hotpost.py`，并挂载到 `/api` 与 `/api/v1`
- 文档补充接口路径：`docs/Reddit爆帖速递_产品模块文档.md`

## 接口概要
- `POST /api/hotpost/search`：同步搜索，返回结构化结果
- `GET /api/hotpost/result/{query_id}`：获取缓存结果
- `POST /api/hotpost/deepdive`：生成深挖 token（需登录）

## 测试
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test \
PYTHONPATH=backend pytest \
  backend/tests/services/hotpost/test_hotpost_keywords.py \
  backend/tests/services/hotpost/test_hotpost_rules.py \
  backend/tests/schemas/test_hotpost_schema.py \
  backend/tests/models/test_hotpost_models.py \
  backend/tests/api/test_hotpost.py -q
```

结果：9 passed（含少量已知 Deprecation warnings）

## 备注
- 当前实现为同步执行；触发限流会等待窗口释放（未实现队列 SSE）。
- deepdive 仅生成 token 并写入 Redis 种子数据，报告由主系统 `/api/analyze` 生成。

