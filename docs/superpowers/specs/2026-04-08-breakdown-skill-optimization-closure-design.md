# Design: Breakdown Skill Optimization As Closure
Date: 2026-04-08
Branch: current workspace

## Problem Statement

小程序现在的主链已经跑通：

- `📡 信号` 有稳定供给
- `🔍 拆解` 已有 `suggestion -> auto write draft -> human review -> publish`

但当前最明显的产品短板，不是“没有拆解链路”，而是：

- 拆解卡还少
- 拆解草稿的内容质量还没有工程化优化
- 系统能产出 `write draft`，但还没有像 signal 一样，形成一套稳定的 `eval -> judge -> canary -> promote`

所以当前真正的问题不是“要不要再补功能”，而是：

**要不要把拆解卡内容质量，作为小程序收尾版本的最后一刀。**

## Premise Challenges

### 挑战 1：是不是应该继续扩 pack，而不是做 breakdown？

结论：不是。

原因：

- 五个成熟 signal pack 已经够支撑首页主价值
- 再继续横向扩 pack，用户感知增量不如拆解明显
- 当前最可见的缺口是“深度判断还不够稳定”

### 挑战 2：会不会把范围做大，影响稳定主链？

结论：会，如果范围不锁死。

所以必须明确：

- 只做 **breakdown content quality optimization**
- 不碰 breakdown supply 主链
- 不碰 suggestion 门槛
- 不碰 auto materialize 机制
- 不碰自动 publish

### 挑战 3：它值不值得当“收尾版本”？

结论：值得。

因为它满足三个条件：

1. 不会改坏当前稳定产卡主链
2. 能直接补产品最明显的价值短板
3. 做完后，小程序会从“有信号、有少量拆解”升级到“拆解也开始有质量护栏”

## Options Considered

| 方案 | What | Effort | Risk | Best for |
|---|---|---:|---:|---|
| A. 继续扩 pack | 再做更多 signal pack | M | 中 | 想继续横向扩内容面 |
| B. 做 breakdown skill optimization | 给拆解卡建立 `eval -> judge -> canary -> promote` | M | 中 | 想补产品最明显的深度短板 |
| C. 只回到稳态运营 | 不再开新优化，继续日更 | S | 低 | 想先停工程投入 |

## Chosen Direction

选 **B. breakdown skill optimization**，作为小程序收尾版本。

原因：

- `signal` 已经有五个成熟 pack，底座够了
- `breakdown V2` 主链已经跑通，正好有土壤接内容质量优化
- 这一步是“纵向补深”，不是“横向再扩功能”
- 对用户来说，这一刀的感知价值比继续补一个新 pack 更直接

## Success Criteria

这轮做完，至少满足下面 5 条：

1. 建立 `breakdown eval set v1`
2. 完成一轮人工 review + failure taxonomy
3. 有可跑的 `breakdown judge v1`
4. 跑出至少一轮 `breakdown canary`
5. 最终沉淀一套可进主链的稳定写法，或明确写清“当前边界还不足以 promote”

## Risks

### 风险 1：把 scope 做大

缓解：

- 不改 supply
- 不改 suggestion 门槛
- 不加前端新交互

### 风险 2：拆解样本太少

缓解：

- 先只用当前已 materialize 的真实 `write draft`
- 不追求样本大而全，先做小而准的 eval set

### 风险 3：judge 过早自动化

缓解：

- 先做人工 review
- 先让 judge 成为“内容质量 gate”
- 不让 judge 决定 publish

## NOT in Scope

- 不做新的 pack 扩展
- 不做新的 breakdown supply 规则
- 不做 suggestion 聚类重写
- 不做前端功能扩展
- 不做全自动 autoresearch
