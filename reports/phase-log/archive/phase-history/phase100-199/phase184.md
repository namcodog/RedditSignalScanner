# Phase 184 - Hotpost 联调验收与阻塞修复

日期：2026-01-29

## 本阶段目标
- 完成 Reddit 爆帖速递前后端联调验收，跑通一次真实查询与 deepdive 入口。

## 主要改动
- 补齐 crawler_runs / crawler_run_targets ORM 映射，避免 evidence_posts 外键解析报错：
  - `backend/app/models/crawler_run.py`
  - `backend/app/models/crawler_run_target.py`
  - `backend/app/models/__init__.py`
- hotpost 写入 discovered_communities 前统一规范化社区名，并在 community_pool 不存在时跳过写入（避免 FK 报错）：
  - `backend/app/services/hotpost/repository.py`
- 新增回归测试：
  - `backend/tests/models/test_crawler_run_models.py`
  - `backend/tests/services/hotpost/test_hotpost_repository.py`

## 数据库迁移 / 环境处理
- `alembic upgrade heads` 失败（权限不足：posts_raw），因此仅执行：
  - `alembic upgrade 20260128_000001`（确保 hotpost 表已落地）
- 生成测试账号：`make seed-test-accounts`（用于 deepdive 登录验收）

## 联调验收结果
- 后端/前端服务均可访问（8006/3006）。
- 查询 1（中文原问）：`最近 AI 工具领域有什么热门讨论？`
  - 返回 0 条（符合“仅英文语料”口径）。
- 查询 2（英文验证）：`AI tools`
  - 成功返回，summary: “找到 30 条相关讨论，来自 2 个社区。”
  - evidence_count=30，confidence=high。
- Deepdive：成功生成 token（TTL=1800s）。

## 已知限制 / 风险
- discovered_communities 受 FK 约束（必须在 community_pool 中存在）；当前 hotpost 发现新社区会被跳过写入。
- hotpost 返回的 communities 仍是 Reddit 原始名称（不含 r/ 前缀），前端跳转链接可能需要补 r/ 规范化。

## 测试
```bash
PYTHONPATH=backend pytest backend/tests/models/test_crawler_run_models.py -q
DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/reddit_signal_scanner_test \
PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_repository.py -q
```

结果：2 passed（含少量 pytest 警告）
