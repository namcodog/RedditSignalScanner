# Phase 760 - 潜力快帖第二批语义刷新

时间：2026-04-11 01:24 CST

## 发现

- 第二批潜力快帖 dry-run 里，浏览器代理卡的 `why_test_now` 出现了截断英文原话 `...`，不能进入前台。
- `--apply` 会重新请求 LLM，因此 apply 结果和 dry-run 样本不完全一致，存在轻微语义漂移。

## 修复

- `card_content_rules.yaml` 增加 `why_test_now` 截断门禁：
  - `...`
  - `…`
- 触发后沿用 Phase 759 的字段校验失败自动重写一次。
- 第二批按 `card_id` 精确刷新 3 张 `lane=signal` 卡：
  - `card-cand-ai-automation-1sfedx0-validate`
  - `card-cand-ecommerce-sellers-1sakv3t-validate`
  - `card-cand-ai-automation-1sfoaf4-validate`

## 验证

- `cd backend && pytest tests/services/hotpost/test_card_content_generator.py::test_generate_card_content_retries_when_field_copy_hits_banned_pattern tests/services/hotpost/test_published_card_semantic_refresh.py -q --tb=short -p no:schemathesis`
- `cd backend && python scripts/hotpost/refresh_published_card_semantics.py --card-id ... --apply --json`
- `cd backend && python scripts/hotpost/push_mini_snapshot.py && python scripts/hotpost/check_mini_release_sync.py`

结果：

- 定向测试 5 passed。
- published 总数仍为 125，`lane=signal` 仍为 48。
- 第二批 3 张写回成功，`published_at / lane / card_type` 均保留。
- mini snapshot 同步通过，release 为 `release-03daa6484bce`，cloud_db copy guard 为 ok。

## 下一步

- 继续刷新前，先补 CLI 的结果锁定能力：
  - `--output-plan <file>`：dry-run 把刷新结果落盘。
  - `--apply-plan <file>`：apply 同一份已审结果，不再二次请求 LLM。
- 这样才能稳定做到“用户审核了什么，就写回什么”。
