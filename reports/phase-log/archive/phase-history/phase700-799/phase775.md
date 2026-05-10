# Phase 775

## 时间

- 2026-04-12

## 本轮目标

- 在不动生产 `signal` 主链的前提下，用 `Gemini CLI / gemini-3.1-pro-preview` 单独跑一轮 `v8` autoresearch
- 先重建 Gemini CLI baseline，再和 `v8` 做同后端 apples-to-apples 比较

## 执行结果

- 已新增 Gemini CLI 专用 runner：
  - `/Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_baseline_v1_gemini_cli.py`
  - `/Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_variant_gemini_cli.py`
- 已新增单变量 `v8` 变体：
  - `/Users/hujia/key-os/04-runtime/autoresearch/variants/reddit-signal-scanner-signal-single-voice-evidence-floor-v8.md`
- Gemini CLI baseline 已跑完：
  - `accept=43.48%`
  - `rewrite=26.09%`
  - `fail=30.43%`
  - `value=69.57%`
  - `banned=30.43%`
- Gemini CLI `v8` 已跑完：
  - `accept=39.13%`
  - `rewrite=21.74%`
  - `fail=39.13%`
  - `value=60.87%`
  - `banned=26.09%`

## 关键判断

- `Gemini CLI` 这条实验线技术上已经跑通，可以作为独立 autoresearch backend。
- 但当前它的 `signal baseline` 明显弱于现有 API 线 `v6 champion`。
- `v8` 也没有在 Gemini CLI 线上赢过 baseline：
  - `accept` 回落
  - `value` 回落
  - `clarity_logic` 和 `anti_template` 也回落
- 当前正确结论：
  - 生产继续保持纯 `v6 champion`
  - `Gemini CLI` 不进入生产主线
  - `v8 discard`

## 涉及文件

- `/Users/hujia/key-os/04-runtime/autoresearch/variants/reddit-signal-scanner-signal-single-voice-evidence-floor-v8.md`
- `/Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_baseline_v1_gemini_cli.py`
- `/Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_variant_gemini_cli.py`
- `/Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-card-quality-v1-results.md`
- `/Users/hujia/key-os/02-projects/active/reddit-signal-scanner.md`

## 验证

- `python3 -m py_compile /Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_baseline_v1_gemini_cli.py /Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_variant_gemini_cli.py`
- `python3 /Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_baseline_v1_gemini_cli.py --generator-model gemini-3.1-pro-preview --generator-timeout-seconds 180 --concurrency 2`
- `python3 /Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_signal_card_quality_evaluator_v1.py --input /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-card-quality-v1-gemini-cli-baseline-outputs.jsonl --output-jsonl /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-card-quality-v1-gemini-cli-baseline-predictions.jsonl --summary-json /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-card-quality-v1-gemini-cli-baseline-summary.json`
- `python3 /Users/hujia/key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_variant_gemini_cli.py --variant-id single_voice_evidence_floor_signal_v8 --variant-prompt /Users/hujia/key-os/04-runtime/autoresearch/variants/reddit-signal-scanner-signal-single-voice-evidence-floor-v8.md --output-jsonl /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-single-voice-evidence-floor-v8-gemini-cli-outputs.jsonl --generator-model gemini-3.1-pro-preview --generator-timeout-seconds 180 --concurrency 2`
- `python3 /Users/hujia/key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_signal_card_quality_evaluator_v1.py --input /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-single-voice-evidence-floor-v8-gemini-cli-outputs.jsonl --output-jsonl /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-single-voice-evidence-floor-v8-gemini-cli-predictions.jsonl --summary-json /Users/hujia/key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-single-voice-evidence-floor-v8-gemini-cli-summary.json`

## 下一步

- 不继续往 `v8` 上补
- 保持生产 `signal` 在 API 线 `v6 champion`
- 如果继续做 `v9+`，先重做实验设计，重新判断：
  - “单人弱证据外推”到底该由生成 prompt 负责
  - 还是该更多交给 evaluator / gate / 后处理
