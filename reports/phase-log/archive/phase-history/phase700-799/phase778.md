# Phase 778

## 目标

把 `signal` 的当前正式路线收口，不再继续摇摆。

## 结论

- `signal v1.0` 正式路线冻结为：
  - 生成后端：`xiaomi/mimo-v2-pro`
  - 生产冠军：`narrow_actor_rule_shift_signal_v6`

## 实验线简记

- `Gemini CLI / gemini-3.1-pro-preview`
  - 已接通并完成对比
  - 当前质量弱于正式生产线
  - 不启用

- `Codex CLI / gpt-5.4-mini + low`
  - 已接通完整 `signal autoresearch` 流程
  - baseline 与 `v6` 都已产出正式 summary
  - 当前质量明显弱于正式生产线
  - 不启用

## 当前口径

- 生产继续用 `mimo + v6`
- 其他模型线只保留为研究线
- 后续若继续做 `signal`，只能在实验线开新变体，不能动当前 `v1.0`
