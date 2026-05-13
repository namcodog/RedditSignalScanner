# Phase 777

## 目标

把 `signal` 的 `gpt-5.4-mini + low` 免费 CLI 路线接到和 `v6` 一样的 autoresearch 流程里，确认它能不能不走 API key 跑完整 baseline / variant / evaluator。

## 本次改动

- 新增 `signal` 的 Codex CLI baseline runner：
  - `key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_baseline_v1_codex_cli.py`
- 新增 `signal` 的 Codex CLI generic variant runner：
  - `key-os/04-runtime/autoresearch/runners/run_reddit_signal_scanner_signal_variant_codex_cli.py`
- 给 `signal card quality evaluator v1` 增加 `codex` judge backend：
  - `key-os/04-runtime/autoresearch/evaluators/reddit_signal_scanner_signal_card_quality_evaluator_v1.py`
- 修正 `CodexCLIChatClient` 的超时回收：
  - timeout 时按进程组 kill，避免 vendor 子进程变孤儿卡死整轮
  - 文件：`backend/app/services/llm/clients/codex_cli_client.py`

## 验证

- `py_compile`
  - `backend/app/services/llm/clients/codex_cli_client.py`
  - `key-os/.../reddit_signal_scanner_signal_card_quality_evaluator_v1.py`
  - `key-os/.../run_reddit_signal_scanner_signal_baseline_v1_codex_cli.py`
  - `key-os/.../run_reddit_signal_scanner_signal_variant_codex_cli.py`
- `pytest`
  - `backend/tests/services/llm/test_llm_clients.py`
  - `backend/tests/services/hotpost/test_signal_cli_shadow.py`
  - `backend/tests/scripts/hotpost/test_run_signal_shadow_compare.py`
  - 结果：`14 passed`
- `pytest`
  - `key-os/04-runtime/autoresearch/tests/test_signal_card_quality_evaluator_v1.py`
  - 结果：`4 passed`

## 正式结果

### Codex CLI baseline

- 结果文件：
  - `key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-card-quality-v1-codex-baseline-summary.json`
- 核心指标：
  - `accept = 4.35%`
  - `rewrite = 43.48%`
  - `banned = 34.78%`

### Codex CLI v6

- 结果文件：
  - `key-os/04-runtime/autoresearch/results/reddit-signal-scanner-signal-narrow-actor-rule-shift-v6-codex-cli-summary.json`
- 核心指标：
  - `accept = 8.70%`
  - `rewrite = 39.13%`
  - `banned = 26.09%`

## 结论

- `gpt-5.4-mini + low` 已经可以作为免费 `signal` autoresearch backend 完整跑流程。
- 但当前质量明显弱于生产里的 `mimo + v6`。
- `v6` 在同一 Codex CLI 线上确实比 baseline 略好，但改善幅度不足以支撑切生产。
- 当前正确口径：
  - 生产继续用 `mimo + v6`
  - `Codex CLI / gpt-5.4-mini + low` 作为独立研究线继续打磨
