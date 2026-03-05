# Phase 232 — Phase J/K/L 最后一轮清理（2026-03-05）

## 背景
按指令执行三件事：
- Phase J：消除 `reporting/` 与 `report/` 目录歧义，移除 `community_discovery.py` compat shim。
- Phase K：为 6 处 Makefile 死引用加 `FIXME` 注释。
- Phase L：修复根 `Makefile` 中旧 `scripts/*.py` 路径到 Phase I 域目录路径。

## 执行明细

### Phase J
1. `git mv backend/tests/services/reporting/test_opportunity_report.py -> backend/tests/services/report/test_opportunity_report.py`
2. 确认 `backend/app/services/community_discovery.py` 为纯转发 shim（仅 docstring + `from ... import *`）
3. 修改 `backend/app/tasks/discovery_task.py` import：
   - `from app.services.community_discovery import CommunityDiscoveryService`
   - -> `from app.services.community.community_discovery import CommunityDiscoveryService`
4. `git rm backend/app/services/community_discovery.py`
5. 清理空目录残留：删除 `backend/tests/services/reporting/__pycache__` 后移除 `backend/tests/services/reporting/`

### Phase K
在以下位置添加死引用注释：
1. `makefiles/dev.mk`（`scripts/trigger_incremental_crawl.py`）
2. `makefiles/test.mk`（`scripts/check_breaking_changes.py`）
3. `makefiles/test.mk`（`scripts/test_contract.py` 文本提示）
4. `makefiles/acceptance.mk`（`scripts/final_acceptance.py`）
5. `makefiles/acceptance.mk`（`scripts/admin_pool_count.py`）
6. `makefiles/acceptance.mk`（`scripts/import_seed_to_db.py`）

注释统一为：
`# FIXME: <path> does not exist (dead reference)`

### Phase L
扫描并修复根 `Makefile` 旧脚本路径为 Phase I 域路径，涉及：
- `refresh_mining_views.py -> scripts/infra/refresh_mining_views.py`
- `db_guard.py -> scripts/infra/db_guard.py`
- `smart_crawler_workflow.py -> scripts/crawl/smart_crawler_workflow.py`
- `crawl_once.py -> scripts/crawl/crawl_once.py`
- `check_celery_health.py -> scripts/monitor/check_celery_health.py`
- `verify_celery_config.py -> scripts/monitor/verify_celery_config.py`
- `local_acceptance.py -> scripts/seed/local_acceptance.py`
- `monitor_crawl_progress.py -> scripts/monitor/monitor_crawl_progress.py`
- `seed_test_accounts.py -> scripts/seed/seed_test_accounts.py`
- `kag_acceptance.py -> scripts/seed/kag_acceptance.py`
- `ingest_jsonl.py -> scripts/import/ingest_jsonl.py`
- `run_semantic_pipeline.py -> scripts/semantic/run_semantic_pipeline.py`
- `t1_data_audit.py -> scripts/report/t1_data_audit.py`
- `generate_t1_market_report.py -> scripts/report/generate_t1_market_report.py`

## 验证结果
按任务给定命令验证：
1. `backend/tests/services/reporting/`：`REMOVED OK`
2. `backend/tests/services/report/`：包含 `test_opportunity_report.py`
3. `backend/app/services/community_discovery.py`：`REMOVED OK`
4. `backend/app/services/*.py`：无根级 `.py`（`NO ROOT *.py (OK)`）
5. `backend/app/tasks/discovery_task.py`：import 已更新为 `app.services.community.community_discovery`
6. `pytest --collect-only`：`835 tests collected, 9 errors`
   - 本次未改业务逻辑，未处理既有 collection 错误。

## 统一反馈（5问）
1) 发现了什么？
- `reporting/` 与 `report/` 确实并存且语义重复；`community_discovery.py` 确认为纯 compat shim；多处 Makefile 存在脚本死引用与旧路径残留。

2) 是否需要修复？
- 需要。否则目录语义混乱、兼容层冗余、Make 命令路径可持续误导。

3) 精确修复方法是什么？
- 仅执行结构清理与注释/路径修复：`git mv`、单行 import 替换、`git rm` shim、Makefile `FIXME` 标注、根 Makefile 路径映射替换。

4) 下一步系统性的计划是什么？
- 对 `pytest --collect-only` 的 9 个既有错误单独开修复 phase，避免与本轮“只做结构清理”混改。

5) 这次执行的价值是什么？达到了什么目的？
- 统一测试目录语义、移除冗余兼容层、提高 Makefile 脚本路径一致性，降低后续 AI/人工维护时的路径歧义与误判概率。
