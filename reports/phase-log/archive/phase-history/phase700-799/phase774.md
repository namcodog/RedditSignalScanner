# Phase 774

## 时间

- 2026-04-12

## 本轮目标

- 把 `signal` 生产 prompt 收回到纯 `v6 champion` 回灌版
- 基于 live 抽样里暴露的 3 个问题起 `v7` autoresearch
- 同步更新 evaluator / harness，重新比较 `v6` 和 `v7`

## 执行结果

- `signal` 生产 prompt 已收回到纯 `v6` 回灌版，没有继续把 live 补口混进生产
- 新建 `signal live-guard v7` 变体，专门解决 3 个 live 问题：
  - 单条反驳评论时 actor 写大
  - `audience` 会拖“尤其是 / 特别是那些”尾巴
  - `why_test_now` 抄截断原话、保留 `...`
- evaluator 已同步升级：
  - `why_test_now` 正式进入 signal card quality evaluator
  - judge prompt 增加上述 3 个 live 问题的失败口径
  - harness 入口已接上 `v7`
- frozen eval set 已补静态 candidate source，解决生产候选池滚动后无法稳定复现实验的问题
- apples-to-apples 结果已跑完：
  - `v6 rejudge v2`：`accept=69.57%`，`rewrite=8.70%`，`fail=21.74%`，`value=78.26%`，`banned=0`
  - `v7`：`accept=56.52%`，`rewrite=8.70%`，`fail=34.78%`，`value=65.22%`，`banned=13.04%`

## 关键判断

- `v6` 本身没有问题，问题在于之前把“冠军回灌”和“线上补口”做成了一件事。
- live 暴露出来的 3 个问题，直接塞回生产 prompt 会明显压缩表达空间。
- `v7` 这轮没有守住主指标，不适合进生产：
  - `accept` 明显回落
  - `value` 明显回落
  - `banned_hit_rate` 从 `0` 升到 `13.04%`
- 当前正确结论是：
  - 生产继续保持纯 `v6 champion`
  - `v7 discard`
  - 后续如果继续试，要从 `v8` 重新做，不再往 `v7` 上硬叠

## 涉及文件

- 生产 prompt：
  - `backend/config/prompt_assets/signal_compact_prompt.md`
  - `backend/config/prompt_assets/signal_field_semantics.md`
- autoresearch：
  - `/Users/hujia/key-os/04-runtime/autoresearch/variants/reddit-signal-scanner-signal-live-guard-v7.md`
  - `/Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_signal_card_quality_evaluator_v1.py`
  - `/Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit-signal-scanner-signal-card-quality-judge-prompt-v1.md`
  - `/Users/hujia/key-os/04-runtime/autoresearch/harnesses/reddit-signal-scanner-signal-card-quality-v1.md`
  - `/Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_autoloop_v1.py`
  - `/Users/hujia/key-os/04-runtime/autoresearch/tests/test_signal_card_quality_evaluator_v1.py`
  - `/Users/hujia/key-os/04-runtime/autoresearch/eval_sets/reddit-signal-scanner-signal-card-quality-v1.json`
  - `/Users/hujia/key-os/04-runtime/autoresearch/eval_sets/reddit-signal-scanner-signal-card-quality-v1-candidates.json`
  - `/Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-card-quality-v1-results.md`

## 验证

- `pytest backend/tests/services/hotpost/test_reddit_guide_prompt_assets.py backend/tests/services/hotpost/test_card_content_generator.py -q --tb=short`
- `python -m pytest /Users/hujia/key-os/04-runtime/autoresearch/tests/test_signal_card_quality_evaluator_v1.py -q`
- `python -m py_compile /Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_signal_card_quality_evaluator_v1.py /Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_autoloop_v1.py`
- `python3 /Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_variant.py --variant-id live_guard_signal_v7 --variant-prompt /Users/hujia/key-os/04-runtime/autoresearch/variants/reddit-signal-scanner-signal-live-guard-v7.md --output-jsonl /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-live-guard-v7-outputs.jsonl`
- `python3 /Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_signal_card_quality_evaluator_v1.py --input /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-live-guard-v7-outputs.jsonl --output-jsonl /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-live-guard-v7-predictions.jsonl --summary-json /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-live-guard-v7-summary.json`
- `python3 /Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_signal_card_quality_evaluator_v1.py --input /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-narrow-actor-rule-shift-v6-outputs.jsonl --output-jsonl /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-narrow-actor-rule-shift-v6-predictions.rejudge-v2.jsonl --summary-json /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-narrow-actor-rule-shift-v6-summary.rejudge-v2.json`

## 下一步

- `signal` 生产继续保持纯 `v6 champion`
- 如果继续 autoresearch，从 `v8` 新开，不再在 `v7` 上继续堆补口
- 下一轮变体优先解决“不要压缩表达空间”的前提下，处理 live 守门问题
