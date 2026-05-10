# Signal Pack Readiness Audit V1

## 目标

确认当前最差的两个 pack 是否已经具备进入定向 `signal skill` 实验的条件。

- `business-growth-ops / paid-economics`
- `ai-automation / tools-efficiency`

## 结果

### `business-growth-ops / paid-economics`

- candidate 数：`3`
- 通过 `signal input quality gate` 的 case：`0`
- 被拦截：`3`

拦截原因全部一致：

- `single_thread_weak_evidence`
- `single_community_weak_evidence`

### `ai-automation / tools-efficiency`

- candidate 数：`3`
- 通过 `signal input quality gate` 的 case：`0`
- 被拦截：`3`

拦截原因：

- 其中 1 条包含：
  - `no_substantive_quotes`
  - `single_thread_weak_evidence`
  - `single_community_weak_evidence`
- 其余 2 条包含：
  - `single_thread_weak_evidence`
  - `single_community_weak_evidence`

## 关键判断

### 1. 这不是 prompt 问题

这两个 pack 当前连 `signal skill` 实验盘子都进不来。

也就是说：

- 问题不在“怎么写”
- 而在“这批输入根本不配写”

### 2. 这两个 pack 当前的主问题是供给，不是文案

当前候选的共同问题不是标题差、summary 差，而是：

- 单帖
- 单社区
- quote 证据弱
- 部分样本连 substantive quote 都没有

这意味着：

- 继续做 pack 定向 prompt 优化没有意义
- 应该回到 pack 供给侧做修复

### 3. 现在不该放松 quality gate

这次 audit 反而说明 `signal input quality gate` 是对的。

如果为了让这两个 pack 能进实验就放松闸门，只会把：

- 弱证据样本
- bot / 公版 / 闲聊样本

重新放回 signal 生成链。

## 结论

当前阶段：

- `paid-economics` 不具备进入定向 signal skill 实验的条件
- `tools-efficiency` 也不具备

下一步主线应改为：

- 修这两个 pack 的输入供给
- 不是继续调 signal prompt
