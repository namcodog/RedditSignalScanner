# Phase 121 - 未被 Makefile/文档引用脚本归档（链路收口）

日期：2026-01-20

## 目标（说人话）
把“没有被 Makefile 或文档引用”的脚本从主路径挪走，避免误用旧脚本，让运行入口更清晰。

## 执行范围
- 扫描入口：Makefile、makefiles、docs/（非 archive）、README 等文档 + 代码内脚本路径引用
- 归档对象：未被上述入口引用的脚本
- 不动：仍被引用的脚本、`backend/scripts/maintenance/__init__.py`、`backend/scripts/LEGACY.md`

## 归档结果
### 1) 根目录 scripts/ 未被引用脚本
- 已移动到：`scripts/archive/orphans/`
- 清单文件：`reports/phase-log/phase121_unreferenced_root_scripts.txt`

### 2) backend/scripts 未被引用脚本
- 已移动到：`backend/scripts/legacy/orphans/`
- 清单文件：`reports/phase-log/phase121_unreferenced_backend_scripts_filtered.txt`

## 结构性补充
- 更新 `scripts/archive/README.md` 增加 orphans 说明
- 更新 `backend/scripts/LEGACY.md` 增加 orphans 说明

## 影响范围
- 仅移动/归档脚本，不涉及业务代码与数据库

## 待确认/下一步
- 如需继续深度收口，可新增“手工可用但未文档化”的脚本白名单，以避免历史脚本被误删或误用。
