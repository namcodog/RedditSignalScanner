# Phase 765 - 已发布 signal 语义重刷启动

## 发现

- 新的 `signal` 语义合同已经接回主链，可以开始批量重刷已发布卡。
- 第一批按 `lane=signal` 直接 dry-run 10 张后，最终筛出 8 张过线卡。
- 第二批按明确 `card_id` 再跑一组，实际有 5 张产生了可合并变化。
- `push_mini_snapshot.py` 和 `check_mini_release_sync.py` 不能并行跑；并行时 `check` 会读到旧 release。

## 执行

### Batch 4

- dry-run plan:
  - `backend/tmp/signal-semantic-refresh-batch4.json`
- apply plan:
  - `backend/tmp/signal-semantic-refresh-batch4-apply.json`
- 写回 8 张：
  - `card-cand-business-growth-ops-1sh3zk6-validate`
  - `card-cand-business-growth-ops-1sgpnzx-validate`
  - `card-cand-ai-automation-1sfedx0-validate`
  - `card-cand-ecommerce-sellers-1sakv3t-validate`
  - `card-cand-ai-automation-1sfoaf4-validate`
  - `card-cand-business-growth-ops-1sffply-validate`
  - `card-cand-ecommerce-sellers-1sbesy3-validate`
  - `card-cand-business-growth-ops-1sggds7-validate`
- 扣下两张未写回：
  - `card-cand-ai-automation-1sdstmx-validate`
  - `card-cand-ai-automation-1saf5hi-validate`

### Batch 5

- dry-run plan:
  - `backend/tmp/signal-semantic-refresh-batch5.json`
- 这轮指定了 10 个后续 `card_id`，实际只有 5 张产生可合并变化
- 写回 5 张：
  - `card-cand-business-growth-ops-1sg3fns-validate`
  - `card-cand-ecommerce-sellers-1sguh0c-validate`
  - `card-cand-business-growth-ops-1rw66wi-validate`
  - `card-cand-ecommerce-sellers-1sg136g-validate`
  - `card-cand-ecommerce-sellers-1sfu9we-validate`

## 结果

- 本次累计新写回已发布 `signal` 卡：`13` 张
- 最新 mini release：
  - `release-31066ab3b9f3`
- 同步校验：
  - `cloud_db copy guard: ok`
  - `feed_contract=30/30 expected=30/30 status=ok`

## 当前判断

- 这条线已经从“验证合同是否生效”进入“批量刷已发布卡”的阶段。
- 当前节奏可行：一批先 dry-run 5 到 10 张，再人工扣掉明显没收住的卡，剩下的直接 apply。
- 下一步优先继续刷剩余 `signal`，再回头处理被扣下的 `1sdstmx / 1saf5hi` 这种需要额外精修的卡。
