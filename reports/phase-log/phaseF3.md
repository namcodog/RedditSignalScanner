# Phase F3 — tests/services 根目录测试文件分域搬迁（2026-03-05）

## 基线回顾
- 参考上一阶段记录：`reports/phase-log/phaseF1.md`
- Phase F1 已建立安全测试入口 `scripts/safe_pytest.sh`（默认 collect-only，强制 `SKIP_DB_RESET=1`）。
- 本阶段目标：把 `backend/tests/services/` 根目录散落测试文件，按域搬到子目录，提升可维护性和定位效率。

## 本次执行
1. 新建目录并补包初始化：
- `backend/tests/services/crawl/__init__.py`
- `backend/tests/services/community/__init__.py`
- `backend/tests/services/infrastructure/__init__.py`

2. 按规则执行 `git mv`（仅移动，不改内容）：
- 共移动 `104` 个测试文件。
- 分域统计：
  - `analysis/`: 26
  - `crawl/`: 25
  - `community/`: 9
  - `infrastructure/`: 10
  - `semantic/`: 17
  - `report/`: 14
  - `labeling/`: 3

3. 按规则保留在根目录（未移动）：
- 明确保留（跨域/特殊）：
  - `test_dual_write_current_violation.py`
  - `test_layer_router.py`
  - `test_backfill_status_service.py`
- 不明确归属，暂留根目录：
  - `test_candidate_vetting_service.py`
  - `test_discovery_auto_backfill_service.py`
  - `test_evaluator_service.py`
  - `test_facts_slice.py`
  - `test_facts_v2_midstream.py`
  - `test_facts_v2_quality_gate.py`
  - `test_hybrid_retriever.py`
  - `test_scoring_rules_loader_layering.py`
  - `test_scoring_rules_need_weights.py`
- 同名冲突暂留：
  - `test_semantic_scorer.py`（`semantic/` 目录已存在同名文件，且内容不同，按“有疑问留根目录”处理）

4. conftest / reporting 检查：
- `backend/tests/services/` 下未发现 `conftest.py`，无需更新。
- `backend/tests/services/reporting/` 非空（存在 `test_opportunity_report.py`），因此未删除该目录。

## 验证
- 执行命令：`SKIP_DB_RESET=1 ./scripts/safe_pytest.sh`
- 结果：`861 collected / 8 skipped`，无 collection error。

## 统一反馈（5问）
1) 发现了什么？
- `tests/services` 根目录存在大量可分域测试文件，结构不统一；同时存在 1 个同名冲突文件（`test_semantic_scorer.py`）。

2) 是否需要修复？
- 需要。否则测试定位成本高，目录语义不一致，后续维护难度持续增加。

3) 精确修复方法？
- 新建缺失域目录并补 `__init__.py`，按命名规则仅用 `git mv` 搬迁；冲突和不明确归属文件保留根目录。

4) 下一步系统性计划是什么？
- Phase F4 建议处理根目录剩余 13 个文件：
  - 明确归属后继续分域；
  - 对 `test_semantic_scorer.py` 两个版本做人工合并策略（保留哪一个或改名拆分）。

5) 这次执行的价值是什么？达到了什么目的？
- 在不改测试逻辑的前提下完成大规模结构整理（104 个文件），把测试入口按业务域归位，降低后续排障和回归验证成本。
