# Remaining Packs CEO Review
Date: 2026-04-08

## 方案愿景

目标不是把所有 pack 都“做出来”，而是把真正值得做、且当前系统做得出来的 pack 逐个成熟化。

12 个月理想状态：

```text
当前状态
- 3 个成熟 pack：paid-economics / selection-signals / agent-builder
- 1 条可用 breakdown V2 主链

这次 delta
- 继续把剩余 pack 做成熟度分层
- 只推进“高价值 + 高可实现性”的 pack

12 个月理想状态
- 不是 9 个 pack 都有专用写法
- 而是 4-5 个真正高价值 pack 成熟
- 其余 pack 保持通用基线或冻结
```

## 前提挑战

### 1. 这是对的问题吗？

不完全是。

真正的问题不是“剩余 pack 要不要全补全”，而是：

- 哪些 pack 值得拥有专用写法
- 哪些 pack 只配继续走通用基线
- 哪些 pack 现在连实验盘子都不够

### 2. 真实目标是什么？

真实目标不是 pack 数量变多，而是：

- 产品价值继续上升
- 系统不因为盲目扩 pack 再次回到“在垃圾输入上做文案体操”

### 3. 如果什么都不做会怎样？

- 不会影响当前主链稳定
- 但会错过把 `signal` 优势继续扩成“多 pack 成熟能力”的窗口

所以：

- 不是必须立刻全做
- 但也不该完全停住

## 方案替代

### 方案 A：全部剩余 pack 一起推进

- 工作量：XL
- 风险：高
- 优点：
  - 覆盖面最大
  - 看起来进展很快
- 缺点：
  - 会把成熟 pack、未成熟 pack、低价值 pack 混在一起
  - 很容易重新掉回“供给不够也硬做实验”
  - 产出会失真

### 方案 B：精选扩展，只做下一批值得做的 pack

- 工作量：M
- 风险：中
- 优点：
  - 成功率高
  - 能复制已经跑通的方法
  - 不会污染现有稳定资产
- 缺点：
  - 覆盖面没那么大
  - 需要接受“有些 pack 现在不做”

### 方案 C：先停 pack，直接开 breakdown 新优化

- 工作量：M
- 风险：中
- 优点：
  - 直接补产品最显著短板
  - 用户感知深度更强
- 缺点：
  - 新的 breakdown 供给会依赖 pack 成熟度
  - 如果 pack 土壤不够厚，breakdown 提升会受限

## 推荐

推荐 **方案 B：精选扩展**。

原因：

- 现在已经证明“pack 成熟 -> breakdown 更容易成立”
- 盲目全扩只会稀释质量
- 直接全面转去新一轮 breakdown 优化也太早

## 范围决策表

| 提案 | 工作量 | 决策 | 原因 |
|---|---:|---|---|
| `organic-discovery` | M | 接受 | 用户价值高，且比 `funnel-conversion` 更容易形成真实信号 |
| `category-winds` | M | 接受 | 电商主线的自然延伸，且已有 selection 基础 |
| `upstream-winds` | S/M | 延后 | 更像情报，不像当前最强的需求信号主线 |
| `kill-signals` | S | 不扩专用写法 | 必须保留，但不适合做下一轮主战场 |
| `funnel-conversion` | M/H | 延后 | 容易抓到抱怨，不容易抓到强判断 |
| `tools-efficiency` | M/H | 继续冻结 | 已验证当前成熟度不够，不该继续烧实验成本 |

## 已接受范围

下一轮只推进两个 pack：

1. `organic-discovery`
2. `category-winds`

推进顺序：

1. 先做 `organic-discovery`
2. 再做 `category-winds`
3. 做完后，再决定是不是开启下一轮 `breakdown` 提升，而不是现在就直接全面扩

## 延后项

- `upstream-winds`
- `kill-signals` 的专用写法
- `funnel-conversion`
- `tools-efficiency` 解冻

## 时间线审查

### 第 1 小时（基础）

要先回答：

- 这两个 pack 当前样本盘子厚不厚
- 是供给问题，还是已经到了写法问题

### 第 2-3 小时（核心逻辑）

最容易模糊的地方：

- `organic-discovery` 会不会滑成泛 SEO/观点文
- `category-winds` 会不会变成空趋势

### 第 4-5 小时（集成）

要警惕：

- 没分清“值得继续追的信号”和“好像有道理的行业评论”
- pack 专用写法误伤其他 pack

### 第 6 小时以上（打磨/测试）

需要尽早规划：

- 继续走现有 `eval -> judge -> canary -> promote`
- 不要再发明第二套优化流程

## 最终结论

不要把“剩下的 pack 全补全”当成目标。

正确目标是：

- **只把值得做、且当前做得出来的 pack 继续做成熟**

当前下一轮最合理的范围是：

- `organic-discovery`
- `category-winds`
