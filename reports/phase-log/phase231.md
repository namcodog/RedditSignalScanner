# Phase 231 — 修复 Phase E 后测试导入路径断裂（2026-03-05）

## 背景
Phase E 将服务文件按域迁移到子目录后，测试收集阶段出现大量导入错误（此前记录为 49，本次接手时为 42）。

## 本次执行（按 5 步）
1. `labeling.py -> labeling_service.py` 命名冲突处理：
   - 实际检查发现目标文件已存在：`backend/app/services/labeling/labeling_service.py`。
   - 未重复执行 `mv`，转为修正误替换导致的导入路径冲突。
2. 全量扫描 stale import：
   - 对 `app.services.<old>` 与 `services.<old>`（你给定的完整清单）做逐项扫描。
   - 结果：清单中的旧路径已基本替换；剩余报错来自 `labeling` 命名替换副作用。
3. 精确修复：
   - 修复错误路径 `app.services.labeling.labeling_service.comments_labeling` -> `app.services.labeling.comments_labeling`
   - 修复错误路径 `app.services.labeling.labeling_service_posts` -> `app.services.labeling.labeling_posts`
   - 扩展兼容 shim：`app/services/labeling/labeling_service.py` 重新导出旧接口（`SAMPLE_COLUMNS`、`load_labeled_data`、`sample_posts_for_labeling`、`validate_labels` 等），避免旧导入点失效。
4. 验证：
   - `python -m pytest tests/ -q --co`
   - 结果：`861 tests collected`，导入错误 `0`。
   - 当前仅剩 8 个 `SKIPPED`（脚本模块缺失/非本次导入迁移范围，另有 smart_tagger 已知 skip）。
5. 提交：
   - 按当前任务要求执行 `git add -A && git commit --amend --no-edit`。

## 影响文件（本次直接修复）
- `backend/app/services/labeling/labeling_service.py`
- `backend/app/tasks/comments_task.py`
- `backend/scripts/generate_t1_market_report.py`
- `backend/tests/services/semantic/test_integration_lexicon_classifier.py`

## 统一反馈（5问）
1) 发现了什么？
- 根因不是“清单中所有旧路径都没改”，而是 `labeling` 批量替换时把“模块路径”误替成了“模块下子模块路径”，触发 `ModuleNotFoundError` 与旧接口导出缺失。

2) 是否需要修复？
- 需要。否则测试在 collection 阶段会中断，后续测试无法执行。

3) 精确修复方法是什么？
- 改回正确模块路径；恢复/补齐 `labeling_service.py` 的兼容导出，保证旧导入点继续可用。

4) 下一步系统性计划是什么？
- 把“导入迁移校验”固化为脚本（收集所有 `app.services.<name>` 旧路径并在 CI 阶段阻断）。
- 对 Phase E 迁移后的脚本目录（`backend/scripts/*`）做一次同类路径审计，避免未来回归。

5) 这次执行的价值是什么？达到了什么目的？
- 已把导入层面的 collection 阻断清零，恢复测试收集能力，为后续真实业务测试执行提供稳定入口。
