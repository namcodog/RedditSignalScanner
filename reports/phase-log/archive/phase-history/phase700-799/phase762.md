# Phase 762 - 已发布 signal 语义优化第三批

时间：2026-04-11 08:11 CST

## 发现

- 第三批先对 5 张已发布 `lane=signal` 跑了 `dry-run + output-plan`。
- 其中 2 张不适合直接写回：
  - `card-cand-business-growth-ops-1sffply-validate`
    - `why_test_now` 夹了英文截断原话，读感不稳。
  - `card-cand-ai-automation-1sdstmx-validate`
    - `summary_line` 判断过满，超过了帖子证据本身。
- 另外 1 张可写回卡在 snapshot copy guard：
  - `card-cand-business-growth-ops-1sg3fns-validate`
  - `detail.why_test_now` 仍带 `...`，被 `check_mini_release_sync.py` 拦下。

## 修复

- 从 dry-run plan 里只切出质量过线的 3 张做 apply：
  - `card-cand-ecommerce-sellers-1sbesy3-validate`
  - `card-cand-business-growth-ops-1sggds7-validate`
  - `card-cand-business-growth-ops-1sg3fns-validate`
- 对 `1sg3fns` 再切出单卡 fix plan，只改 `detail.why_test_now`：
  - 去掉英文截断和 `...`
  - 改成中文直说版，不补新事实

## 验证

- `python scripts/hotpost/refresh_published_card_semantics.py --output-plan tmp/signal-semantic-refresh-batch3.json --json`
- `python scripts/hotpost/refresh_published_card_semantics.py --apply-plan tmp/signal-semantic-refresh-batch3-apply.json --json`
- `python scripts/hotpost/refresh_published_card_semantics.py --apply-plan tmp/signal-semantic-refresh-fix-1sg3fns.json --json`
- `python scripts/hotpost/push_mini_snapshot.py`
- `python scripts/hotpost/check_mini_release_sync.py`

结果：

- 第三批实际写回 `3` 张。
- 最新 mini snapshot release：
  - `release-140ad6df1e5a`
- `cloud_db copy guard: ok`
- 发布总数仍为 `125`，只刷新语义，不改发布身份、lane、发布时间。

## 下一步

- 继续按同样节奏做下一批：
  1. 先 `dry-run + output-plan`
  2. 只挑过线卡进入 apply plan
  3. apply 后立刻 `push_mini_snapshot.py + check_mini_release_sync.py`
- 暂缓的 2 张保留在 plan 审核阶段，后续要么重生成，要么单卡人工修句后再进 apply。
