# Phase E — 服务文件目录重构（2026-03-05）

## 目标
将 `backend/app/services/` 根目录中分散的服务文件归类到既有域目录：
- crawl/
- community/
- analysis/
- semantic/
- labeling/
- infrastructure/

并更新全局导入路径。

## 执行结果
- 已将 39/39 目标文件归并到域目录（E1~E5）。
- `community_discovery.py` 保持为兼容 shim，不移位。
- 根目录 `backend/app/services/` 仅剩 `community_discovery.py`。
- 所有批次完成旧路径检查，并按要求进行全量校验。

## 变更
- 约 39 个文件移动（`rename`）
- 约 195 个文件路径引用更新（仅 import/task string 调整，无业务逻辑改动）
- 关键目录新增：`backend/app/services/infrastructure/`

## 校验
- `python -m mypy app --strict`：`71` errors（与本次改动无关，仍需后续逐项清理）
- `python -m pytest tests/ -q --co`：`702 tests collected, 49 errors in collection`

## 提交
- `e0bd4d2`：`refactor: Phase E — organize 39 loose service files into domain subdirectories`
