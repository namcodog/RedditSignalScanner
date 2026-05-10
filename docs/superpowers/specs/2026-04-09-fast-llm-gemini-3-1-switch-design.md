# Design: Fast LLM 全量切到 Gemini 3.1 Flash Lite Preview
Date: 2026-04-09
Branch: main

## Problem Statement
当前 hotpost 主链的 fast LLM 以 `google/gemini-2.5-flash-lite` 为主。用户对它的语义表达仍不满意，认为它“差点意思”，希望评估是否应把主 fast 模型全量切到 `google/gemini-3.1-flash-lite-preview`。

## Premise Challenges
- 问题不只是“模型更强吗”，而是“全量切换后，是否会让稳定供卡更好”。
- 语义更强不等于适合做默认 fast 模型；还要看延迟、超时、稳定性、JSON 结构化成功率。
- 当前系统已经把 `upstream-winds` 和 `paid-economics` 两个弱 override pack 单独路由到 `google/gemini-3.1-flash-lite-preview`，说明 3.1 已经被承认为更强语义模型，但尚未证明适合全量默认。

## Options Considered
### OPTION A: 全量切到 Gemini 3.1 Flash Lite Preview
What: 默认 fast 模型直接改成 `google/gemini-3.1-flash-lite-preview`
Effort: S
Risk: High
Best for: 只追求语义上限，不在乎吞吐、超时和运营稳定性

### OPTION B: 维持默认 2.5，继续白名单 3.1
What: 继续默认 `google/gemini-2.5-flash-lite`，仅弱 override pack 走 3.1
Effort: S
Risk: Low
Best for: 当前稳定供卡阶段

### OPTION C: 扩大 3.1 白名单，但不全量切
What: 默认保持 2.5，同时再挑 1-2 个语义要求高的 pack 试点 3.1
Effort: M
Risk: Med
Best for: 想继续提高语义，但不想把整条主链押上

## Chosen Direction
先不全量切，继续走 OPTION B。

原因：
- 3.1 的语义上限更高，这点已经在现有 pack override 中被承认。
- 但它此前就暴露过更慢、更吃 timeout 的特点。
- 当前产品主矛盾已经从“语义太弱”转成“供给密度和稳定供卡”，这时全量切更重的 fast 模型，会先打吞吐。
- 更合理的路是：保住 2.5 的吞吐，把 3.1 用在最需要理解力的 pack 上。

## Success Criteria
- 默认 fast 模型保持稳定供卡，不因模型切换导致候选处理吞吐明显下降。
- 继续观察 3.1 白名单 pack 的前台读感是否稳定优于 2.5。
- 若未来 3.1 在真实运营中同时满足“语义更好 + 吞吐可接受 + 超时可控”，再讨论全量切。

## Risks
1. 用户继续觉得 2.5 的整体语义不够好
   - Mitigation: 扩大 3.1 的 pack 白名单，而不是全量切。
2. 3.1 白名单 pack 与 2.5 pack 文风差异过大
   - Mitigation: 继续收统一的 polish 规则。
3. 团队误以为“更强模型 = 应该全量替换”
   - Mitigation: 在配置和 SOP 里明确“默认模型”和“白名单覆盖”的区别。

## NOT in Scope
- 本次不直接修改生产 fast 模型配置
- 本次不重新做模型海选
- 本次不放松发布门禁来掩盖模型问题
