# Phase E — services/ 根目录 41 文件域分家（2026-03-05）

> **补充记录**: 本 phase-log 在审计中发现缺失，补写于 2026-03-05 Phase G 审计阶段。

## 基线回顾
- 参考上一阶段记录：`reports/phase-log/229-repo-structure-cleanup-p0p1.md` (Phase A-D)
- Phase A-D 完成了根目录文档归位、API shim 消灭、report/reporting 合并、community_discovery 歧义解决。
- 本阶段目标：把 `backend/app/services/` 根目录散落的约 41 个 .py 文件，按业务域归入子目录。

## 本次执行
1. 按 Phase E1-E5 分 5 批次执行 `git mv`（仅移动 + import 更新，不改业务逻辑）。
2. 新建 9 个域子目录并补 `__init__.py`：
   - `metrics/`, `facts_v2/`, `labeling/`, `discovery/`, `evaluation/`, `ops/`, `export/`, `infrastructure/`, `mock/`
3. 所有 41 个文件归位后，services/ 根目录仅保留 1 个 compat shim（`community_discovery.py`，因有 4 个外部引用未做迁移）。

### 结果统计
- 总域子目录数：17（含原有 8 + 新建 9）
- 全部 16 个业务子目录（排除 `__pycache__`）均有 `__init__.py` ✅
- 根目录残留文件：1（community_discovery.py compat shim）

## 验证
- Serena `list_dir` 确认 services/ 根目录仅 1 文件
- `find services -maxdepth 2 -name "__init__.py"` 确认 16 个 `__init__.py` 存在
- Serena `architecture` + `project_overview` 记忆已同步更新 (Phase G)

## 价值
- 消除了 AI agent 在 services/ 中的寻址困难，41 个同级文件变为 17 个语义清晰的域子目录。
- import 链路从 `services.xxx` 变为 `services.domain.xxx`，域归属一目了然。
