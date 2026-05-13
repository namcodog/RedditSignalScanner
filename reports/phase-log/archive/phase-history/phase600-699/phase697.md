# phase697

## 本轮完成
- 对当前 `signal / validate` 主链做了 `fast_model` A/B 对照：
  - `x-ai/grok-4.1-fast`
  - `deepseek/deepseek-v3.2`
- 固定：
  - 同一批真实候选
  - `HOTPOST_REASONING_ENABLED=0`
  - 不写回生产

## 样本
- `cand-ai-automation-1sfnauw` `upstream-winds`
- `cand-ai-automation-1sd78l0` `agent-builder`
- `cand-ecommerce-sellers-1s9m07l` `selection-signals`
- `cand-business-growth-ops-1sbnkdt` `paid-economics`

## 结论
- `DeepSeek V3.2` 在弱 override、需要自己整合长帖语义的场景下，语义理解略强：
  - 代表样本：
    - `upstream-winds`
    - `paid-economics`
- 但它没有稳定带来更好的前台读感：
  - 会更完整，也更容易写成“复述讨论”
- 在成熟 pack 上，差异被 pack override / polish 基本抹平：
  - `agent-builder`
  - `selection-signals`

## 决策
- 当前不建议把 `deepseek/deepseek-v3.2` 直接全量替换为默认 `fast_model`
- 当前继续保留：
  - `x-ai/grok-4.1-fast`
- 如果后续继续用 DeepSeek，建议只做：
  - 弱 override pack 的窄 canary
  - 或离线实验室用途
