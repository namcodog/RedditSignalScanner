# Phase 759 - 潜力快帖已发布卡小批量语义刷新

时间：2026-04-11 01:07 CST

## 发现

- 直接把已发布潜力快帖批量重刷会有质量风险：早期 dry-run 里仍出现“可以继续看”“广告主或优化师”“特别是那些”这类说明书腔。
- “从业者”如果放进全局 audience 门禁，会误伤历史卡并导致 `check_mini_release_sync.py` copy guard 失败，范围过宽。

## 修复

- 收紧 `signal_compact_prompt.md` 和 `signal_field_semantics.md`：
  - `audience` 不允许泛职业拼盘。
  - `continue_signal` 必须直接写“继续看/后面看”，不写“可以继续观察/建议关注”。
- `card_content_generator.py` 增加字段校验失败后的 LLM 自动重写一次：
  - JSON 合法但字段命中禁词时，不直接失败。
  - 追加错误原因，让模型按同一输入重写完整 JSON object。
- `card_content_rules.yaml` 只保留明确坏句式门禁：
  - `audience`: `特别是那些`, `广告主或优化师`
  - `continue_signal`: `可以继续看`, `可以继续观察`, `可以观察`, `建议关注`
- 用 published 专用窄刷新入口写回 3 张 `lane=signal` 卡：
  - `card-cand-business-growth-ops-1sh3zk6-validate`
  - `card-cand-business-growth-ops-1sgpnzx-validate`
  - `card-cand-ai-automation-1saf5hi-validate`

## 验证

- `cd backend && pytest tests/services/hotpost/test_card_content_generator.py::test_generate_card_content_retries_when_field_copy_hits_banned_pattern tests/services/hotpost/test_published_card_semantic_refresh.py -q --tb=short -p no:schemathesis`
- `cd backend && python scripts/hotpost/refresh_published_card_semantics.py --lane signal --limit 3 --apply --json`
- `cd backend && python scripts/hotpost/push_mini_snapshot.py && python scripts/hotpost/check_mini_release_sync.py`

结果：

- 定向测试 5 passed。
- published 总数仍为 125，`lane=signal` 仍为 48。
- 3 张已发布潜力快帖语义字段写回成功，`published_at / lane / card_type` 均保留。
- mini snapshot 同步通过，release 为 `release-376b5865d377`，cloud_db copy guard 为 ok。

## 下一步

- 继续按 3-5 张一批刷新 `lane=signal`，不要直接全量。
- 每批先 dry-run，再 apply，再 `push_mini_snapshot.py + check_mini_release_sync.py`。
- 若后续仍出现说明书腔，优先收紧 prompt 或字段门禁，不走人工硬编码覆盖。
