# Phase 122 - 入口/口径全量核对（脚本与最高级系统文件）

日期：2026-01-20

## 目标（说人话）
确认当前系统“唯一路径 + 唯一口径”是否存在且正确：
- 哪些脚本是“最新/现行入口”
- 哪些文档是“最高级系统文件”（权威口径）
- 有没有入口指向不存在的脚本/文件（空洞）

## 核对方法（检索到底）
- 扫描范围：Makefile/makefiles、README、docs（非 archive）、代码内脚本路径
- 过滤范围：docs/archive、scripts/archive、backend/scripts/legacy、reports、data/datasets
- 产出：入口脚本清单 + 缺失引用清单 + 模式/目录引用清单

## 最高级系统文件（权威口径）
来自 README “主文档（必读）”与“唯一参照”标注：
1. `README.md`、`AGENTS.md`（入口与规范）
2. `docs/2025-10-10-文档阅读指南.md`（阅读地图与角色路径）
3. `docs/PRD/PRD-INDEX.md` + `docs/PRD/PRD-*.md`（需求与边界）
4. `docs/系统架构完整讲解.md` / `docs/系统架构快速参考.md`（链路与关键路径）
5. `docs/ALGORITHM-FLOW.md`（算法/数据流）
6. `docs/API-REFERENCE.md`（接口权威定义）
7. `docs/2025-10-10-质量标准与门禁规范.md`（质量门禁）
8. `docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md`（抓取口径唯一参照）
9. `docs/sop/2025-12-14-database-architecture-atlas.md`（数据库真相唯一参照）

## 最新/现行脚本（入口引用即有效）
入口引用共 195 条脚本路径，确认存在的有效脚本如下：
- 根目录脚本：50 个（清单见 `reports/phase-log/phase122_latest_scripts_root.txt`）
- 后端脚本：114 个（清单见 `reports/phase-log/phase122_latest_scripts_backend.txt`）
- 前端脚本：3 个（清单见 `reports/phase-log/phase122_latest_scripts_frontend.txt`）
- 目录/模式引用：
  - 目录引用：1 个（见 `reports/phase-log/phase122_script_ref_dirs.txt`）
  - 模式引用：3 个（见 `reports/phase-log/phase122_script_ref_patterns.txt`）

## 入口空洞（引用但不存在）
共 7 条，需要补齐或移除引用：
1. `scripts/daily_quality_check.sh`（README 里引用）
2. `scripts/semantic_lexicon_import.py`（makefiles/tools.mk 引用）
3. `scripts/manual_verification.sh`（PRD-08 引用）
4. `scripts/query_db.py`（docs/DATABASE_CONFIGURATION.md 引用）
5. `scripts/release_gate.sh`（质量门禁规范引用）
6. `scripts/monitor_test_stability.py`（docs/reference/异步事件循环问题完整解决方案.md 引用）
7. `infrastructure/scripts/verify_structure.py`（PRD/ARCHITECTURE 引用，基础设施目录为空）

详见：`reports/phase-log/phase122_missing_script_refs.txt`

## 发现的文档口径不一致
- `docs/2025-10-10-文档阅读指南.md` 仍写“实施清单”最高优先级，但实施清单已归档（需要修正文案，避免误导）。
- `backend/scripts/LEGACY.md` 中仍提到 `scripts/legacy/`，实际路径为 `backend/scripts/legacy/`（需统一表述）。

## 结论
- 最高级系统文件已明确且可追溯。
- 现行脚本入口已列清，但仍有 7 处入口空洞，需要处理后才能说“唯一路径 100% 正确”。
