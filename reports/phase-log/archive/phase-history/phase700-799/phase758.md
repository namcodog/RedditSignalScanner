# Phase 758 - 已发布卡语义刷新安全入口

时间：2026-04-11 00:51 CST

## 发现

- 已发布卡也需要吃到新的语义 prompt 和 ximo 模型，否则前台会同时存在新旧口径。
- 旧 `backfill_hotpost_card_content.py` 会遍历全部 published 并重建整张发布卡，虽然走 `merge_published_cards`，但缺少 dry-run、limit、card-id 和发布元数据保护。
- 已发布卡刷新不能让 signal 自动升级成 breakdown，否则会改变用户已经看到的发布类型和 tab 归属。

## 修复

- 新增 `app/services/hotpost/published_card_semantic_refresh.py`：
  - 用当前 `generate_card_content` 重新生成语义。
  - 只合并 `title / summary_line / audience / why_now / detail` 等语义字段。
  - 保留 `card_id / signal_id / card_type / lane / category_id / published_at / source_module / source_link` 等发布身份和来源字段。
- 新增 `scripts/hotpost/refresh_published_card_semantics.py`：
  - 默认 dry-run。
  - 支持 `--card-id / --lane / --card-type / --limit / --all / --apply / --json`。
  - `--apply` 必须带 selector 或 `--all`，避免误刷全部发布卡。
- 更新 `scripts/backfill_hotpost_card_content.py` 为新 CLI 包装入口，避免继续走旧全量重建逻辑。
- `generate_card_content` 新增 `allow_breakdown=False` 开关，已发布卡语义刷新时不会把 signal 改成 breakdown。

## 验证

- `cd backend && python -m py_compile app/services/hotpost/card_content_generator.py app/services/hotpost/published_card_semantic_refresh.py scripts/hotpost/refresh_published_card_semantics.py scripts/backfill_hotpost_card_content.py`
- `cd backend && pytest tests/services/hotpost/test_published_card_semantic_refresh.py tests/services/hotpost/test_card_content_generator.py::test_generate_card_content_can_disable_breakdown_for_published_refresh -q --tb=short -p no:schemathesis`
- `cd backend && python scripts/hotpost/refresh_published_card_semantics.py --limit 0 --json; test $? -eq 2`

结果：

- 编译通过。
- 5 个定向测试通过。
- CLI 参数错误返回 JSON error，不再输出 Python traceback。

## 使用口径

- 先干跑看差异：
  - `cd backend && python scripts/hotpost/refresh_published_card_semantics.py --limit 5 --json`
- 指定卡写回：
  - `cd backend && python scripts/hotpost/refresh_published_card_semantics.py --card-id <card_id> --apply --json`
- 小批量写回 signal：
  - `cd backend && python scripts/hotpost/refresh_published_card_semantics.py --lane signal --limit 10 --apply --json`
- 写回后再同步小程序：
  - `cd backend && python scripts/hotpost/push_mini_snapshot.py`
  - `cd backend && python scripts/hotpost/check_mini_release_sync.py`
