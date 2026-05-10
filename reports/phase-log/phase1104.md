# phase1104 - CursorAI 探索候选进入草稿

## 这轮达到的目的
把已验收的 `ai-automation` 探索候选推进到草稿层，验证新社区不只停在候选。

## 当前状态变化
- `cand-ai-automation-1t5ef8s` 已 seed 成 `draft-cand-ai-automation-1t5ef8s-validate`，lane=`signal`。
- 草稿已修掉 `why_test_now` 里误抓广告质疑且截断原话的问题。
- R11 dry-run 变为：`r/CursorAI candidate_count=2 / draft_count=1 / published_count=0`。
- 总体仍是 `input_rows=16 / already_in_pool=3 / keep_testing=13 / promote_candidate=0 / reject=0`。

## 还没完成什么
- 没有发布证据，所以 `CursorAI / windsurf` 仍不能进入 R12 写库。
- grouped 候选还在 queue，但与已 seed 的 Cursor 单帖同题，不能重复发。

## 下一步做什么
人工复核 CursorAI 草稿质量；若不发布，继续观察；若发布后再重跑 R11，满足条件再谈 R12。
