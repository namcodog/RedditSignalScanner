# Phase 123 - 入口空洞修复与口径对齐（唯一事实确认）

日期：2026-01-20

## 目标（说人话）
把“引用了不存在脚本”的入口空洞全部修掉，确保路径与口径 100% 对齐，形成唯一事实。

## 修复点（对齐路径）
1) README 日常巡检入口纠正
- `./scripts/daily_quality_check.sh` -> `./scripts/daily_ops_check.sh evening`

2) Makefile 工具入口纠正
- `semantic-lexicon-import` 目标移除对不存在脚本的调用，改为明确提示“脚本未落地”。

3) PRD/质量标准/架构文档口径纠正
- `docs/PRD/PRD-08-端到端测试规范.md`：移除 `scripts/manual_verification.sh`，改为手动命令示例。
- `docs/2025-10-10-质量标准与门禁规范.md`：移除 `scripts/release_gate.sh`，改为现行 Makefile 入口。
- `docs/PRD/ARCHITECTURE.md`：移除不存在的 `infrastructure/scripts/verify_structure.py`，标记为“未落地”。
- `docs/2025-10-10-文档阅读指南.md`：修正文档优先级与更新频率，去除“实施清单”旧口径。

4) 参考文档口径纠正
- `docs/reference/异步事件循环问题完整解决方案.md`：移除 `scripts/monitor_test_stability.py`，改为命令式监控建议。
- `docs/DATABASE_CONFIGURATION.md`：移除 `scripts/query_db.py`，改用 `scripts/db_realtime_stats.sql`。
- `backend/scripts/LEGACY.md`：修正 legacy 路径表述。

## 核对结果（入口空洞归零）
- 缺失脚本引用：0
- 入口清单输出：
  - 根目录脚本：`reports/phase-log/phase123_latest_scripts_root.txt`
  - 后端脚本：`reports/phase-log/phase123_latest_scripts_backend.txt`
  - 前端脚本：`reports/phase-log/phase123_latest_scripts_frontend.txt`
  - 目录/模式引用：`reports/phase-log/phase123_script_ref_dirs.txt` / `reports/phase-log/phase123_script_ref_patterns.txt`

## 影响范围
- 仅修正文档与 Makefile 入口描述，不改业务逻辑与数据库。
