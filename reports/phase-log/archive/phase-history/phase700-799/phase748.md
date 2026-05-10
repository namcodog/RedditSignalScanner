# Phase 748 — 卡片语义与 1.0 密度链路收口

## 发现了什么？

- 语义输出最优先要解耦的是 `card_content_generator` 主链：证据、prompt、LLM 输出、pack 规则、polish 不能继续被 Python override 混在一起。
- 前台信息密度的真堵点之一是展示链路仍写死 `12` 张首屏；即使发布池已有 100+ 张，前端和云函数也会把首屏压薄。
- 旧的 pack override 文件虽然还在历史实验层，但不能再接回主生成链。

## 是否需要修复？

需要，且本轮已修。

## 精确修复方法

- 新增 `semantic_readout` 主层，把“讲人话”和事实边界集中到 YAML + `semantic_readout.py`，主生成链只调用 `semantic_prompt_extra()` 和 `finalize_signal_readout()`。
- `card_content_generator.py` 不再导入或调用 pack override；paid-economics 的生产 variant 路由也改为从 `card_content_rules.yaml` 读取。
- `hotpost_supply_discovery_v2.yaml` 增加 `feed_initial_page_size=30` / `feed_max_page_size=30`。
- backend `/api/hotpost/cards` 默认页大小改为读取 YAML 合同，并拒绝超过合同上限的 `page_size`。
- mini snapshot 增加 `feed_contract`，写入 latest、manifest 相关 release、cloud_db meta、miniRelease bundle、miniFavorites bundle。
- 云函数 `miniRelease` 不再静默 fallback 到 12；缺 `feed_contract` 直接报错，防止前台密度悄悄缩水。
- 小程序 `listCards()` 不再主动传 `pageSize: 12`，由 release 合同决定首屏密度。
- 新增 `test_semantic_readout_boundary.py`，防止主链重新接回旧 override。

## 验证结果

- `python -m py_compile ...` 通过。
- `pytest backend/tests/services/hotpost/test_workflow_dry_run.py backend/tests/services/hotpost/test_source_scope_catalog.py backend/tests/services/hotpost/test_card_content_generator.py backend/tests/services/hotpost/test_semantic_readout_boundary.py backend/tests/scripts/hotpost/test_push_mini_snapshot.py backend/tests/api/test_hotpost_clues.py -q --tb=short -p no:schemathesis` -> `55 passed`。
- `cd hotpost-mini/hotpost-mini-app && node --test cloudfunctions/tests/mini-release.test.mjs` -> `2 passed`。
- `npx tsc --noEmit` 仍有既有 Taro / 依赖类型错误；本轮触碰的 `src/pages/index/index.tsx`、`src/services/clues.ts`、云函数相关文件未再出现错误。

## 当前结果

- 最新 mini release：`release-3322c8490398`
- 已发布卡：`125`
- 前台首屏合同：`30 / 30`
- 最近 30 张 lane：`signal=18 / hot=7 / breakdown=5`
- 最近 30 张领域：`电商=11 / 增长=10 / AI=9`

## 下一步

- 继续补 `hot` 1 张，把 recent30 拉回 `18 / 8 / 4` 附近。
- 继续把旧 override 文件从“历史实验层”迁出主测试语境，避免后续误以为它们仍是生产口径。
- 后续每次发布后必须同时核对：backend latest、miniRelease latest、miniFavorites latest、feed_contract。
