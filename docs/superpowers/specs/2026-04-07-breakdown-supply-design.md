# Design: Breakdown Card Supply
Date: 2026-04-07
Branch: current workspace

## Problem Statement

现在不是“拆解卡写得少”，而是系统默认只会产出单点信号。当前采集链以单帖 candidate 为主，而拆解卡需要多条证据共同指向同一个更深解释。

## Premise Challenges

- 挑战 1：多一点 prompt 润色不会自然变出更多拆解卡。
  - 结论：错。prompt 只能把现有证据写顺，不能凭空补多线程证据。
- 挑战 2：现在拆解少，是不是门槛设太高。
  - 结论：不高。当前门槛是在防止单帖硬写成“深度”。
- 挑战 3：是不是应该直接多发拆解。
  - 结论：不该。会回到“看着深，其实在编”的老问题。

## Options Considered

| Option | What | Effort | Risk | Best for |
|---|---|---:|---:|---|
| A. 降门槛 | 放宽 `thread_count/community_count`，让单帖也能升拆解 | S | High | 追求短期拆解数量 |
| B. 人工组卡 | 运营先把同类 signal 手动组 draft，再发拆解 | M | Low | 立刻提高拆解质量 |
| C. 自动聚类 | 在 candidate 和 draft 之间加“同主题聚合层” | M/L | Med | 稳定提高拆解供给 |

## Chosen Direction

选 **B + C**。

- **短期**：先用人工组卡补拆解供给，别动 prompt，别降门槛。
- **中期**：做自动聚类层，把“更多单点 signal”抬成“可发的拆解卡”。

不选 A，因为它会直接破坏“拆解卡必须有证据压缩”的合同。

## Success Criteria

- 日常 feed 仍以 `📡 信号` 为主，但能稳定出现少量高质量 `🔍 拆解`
- 拆解卡必须来自多 candidate 合并，而不是单帖硬升格
- 运营能够明确知道：哪些信号该继续观察，哪些信号已经够资格合成拆解

## Risks

1. 人工组卡太慢
   - 先限制在高价值 scope：电商、AI builder
2. 自动聚类把不该放一起的帖子硬合并
   - 初期只用保守规则：同 scope + 关键词重合 + 意图接近
3. 为了提高拆解数量，重新滑回“假深刻”
   - 坚守门槛：没有多证据，不升拆解

## NOT in Scope

- 不靠 prompt 把单帖写成拆解
- 不在前端新增“拆解”之外的第三种标签
- 不把“拆解变多”理解成“每天都要发很多深度卡”
