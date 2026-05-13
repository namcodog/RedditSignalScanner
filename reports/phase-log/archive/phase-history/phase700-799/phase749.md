# Phase 749 - 语义旧链路清理与分发合同复核

## 发现

- 审计确认 `signal_skill_experiment.py`、多个 canary 脚本和 mini release 同步检查仍有旧边界残留。
- 主要风险不是线上出卡失败，而是评测/实验链路继续引用 pack-specific override，后续会把语义规则重新写散。
- `check_mini_release_sync.py` 只看 release/card count，没有校验 `feed_contract`，无法提前发现前端密度合同漏同步。

## 修复

- `signal_skill_experiment.py` 改为统一使用 `semantic_readout.semantic_prompt_extra()` 和 `finalize_signal_readout()`。
- 删除旧 pack override 模块与对应测试：`agent_builder / business_growth / category_winds / organic_discovery / paid_econ / selection`。
- `category / agent_builder / organic / selection` canary 全部改成验证当前 semantic readout 主链，不再对比旧 override。
- `check_mini_release_sync.py` 增加 YAML 驱动的 `feed_contract` 校验，backend snapshot、miniRelease、miniFavorites、cloud_db meta 任一缺失或不一致都会非零退出。

## 验证

- `python -m py_compile ...` 通过。
- `pytest backend/tests/services/hotpost/test_signal_skill_experiment.py backend/tests/services/hotpost/test_semantic_readout_boundary.py backend/tests/scripts/hotpost/test_check_mini_release_sync.py -q --tb=short -p no:schemathesis` -> `15 passed`。
- `PYTHONPATH=backend python backend/scripts/hotpost/check_mini_release_sync.py` -> 四个发布面均为 `feed_contract=30/30 status=ok`。
- `pytest backend/tests/services/hotpost/test_workflow_dry_run.py backend/tests/services/hotpost/test_source_scope_catalog.py backend/tests/services/hotpost/test_card_content_generator.py backend/tests/services/hotpost/test_semantic_readout_boundary.py backend/tests/services/hotpost/test_signal_skill_experiment.py backend/tests/scripts/hotpost/test_push_mini_snapshot.py backend/tests/scripts/hotpost/test_check_mini_release_sync.py backend/tests/api/test_hotpost_clues.py -q --tb=short -p no:schemathesis` -> `68 passed`。

## 结论

- 语义输出规则的 canonical 位置现在收束到 `card_content_rules.yaml -> semantic_readout.py`。
- 旧 pack override 不再作为可执行模块存在，避免后续实验链路把硬编码文案带回主链。
- mini 分发同步检查现在能覆盖 `1.0` 信息密度合同，不再只看 release id。
