# Design: 爆贴热点 V1
Date: 2026-04-08
Branch: current

## Problem Statement
当前前台只有两类内容：
- `信号快报`
- `深度信号`

但用户对“大家正在集中讨论什么”的内容也有真实需求。现在系统里这类内容没有独立产品语义，容易出现两种坏结果：

1. 热度内容被硬塞进 `信号快报`，用户觉得“怎么全是吐槽和围观”
2. 为了保住 `信号快报` 的可信度，很多本来有围观价值的高热讨论又发不出来

真正的问题不是“要不要再加一个标签”，而是：

**怎么把“讨论价值优先”的内容单独拉出来，又不污染 `信号快报` 的判断价值。**

## Premise Challenges
### 挑战 1：爆贴热点是不是就是“更热的信号快报”？
不是。

如果只是把一部分现有 `validate` 卡改名为“爆贴热点”，用户前台感知不会有区别。那只是换壳，不是新内容线。

结论：
- `信号快报` 看“值不值得继续追”
- `爆贴热点` 看“现在大家为什么集中在聊这件事”

### 挑战 2：要不要新做第三套完整系统？
现在不值得。

我们已有：
- `signal-ops`
- `breakdown-ops`
- `validate / write` 两条主链

如果现在为热点再做第三套独立 prompt、judge、skill、SOP，复杂度会直接翻倍，而且大概率会和 `信号快报` 自相残杀。

结论：
- V1 不做第三套大系统
- 先作为 `validate` 下的一条新 lane 接入

### 挑战 3：热点内容是不是只要热就发？
不是。

纯社区礼仪吐槽、纯梗图、纯发泄、纯标题党抱怨，都不能进。

结论：
**爆贴热点不是“什么火发什么”，而是“有讨论焦点的高热帖子”。**

## Options Considered
### OPTION A: 只保留信号快报，不做热点线
What: 继续只做 `信号快报 + 深度信号`
Effort: S
Risk: Medium
Best for: 只想守住判断价值，不在乎围观型内容

问题：
- 用户对热点内容的需求无法承接
- 高热讨论会继续要么混进 signal，要么被全部压掉

### OPTION B: 爆贴热点做成 validate 的第二条 lane
What: 保留现有 `validate / write` 主链，在 `validate` 下新增 `lane=hot`
Effort: M
Risk: Low
Best for: 先用最小代价把热点线跑起来

优点：
- 最适配现有 workflow 和 skills
- `signal-ops` 可以兼容，不需要第三套系统
- 不污染 `深度信号`

### OPTION C: 爆贴热点做成第三套独立系统
What: 独立 prompt、judge、skill、SOP、前台结构
Effort: L
Risk: High
Best for: 热点线已经成熟、量大、价值明确的时候

问题：
- 现在过早
- 复杂度和维护成本太高
- 容易和 `信号快报` 重叠

## Chosen Direction
选 **OPTION B**。

V1 做法：
- 保留底层 `card_type`
  - `validate`
  - `write`
- 在 `validate` 下新增轻字段：
  - `lane=signal`
  - `lane=hot`
- `write` 继续等于 `深度信号`

前台映射：
- `validate + lane=signal` -> `信号快报`
- `validate + lane=hot` -> `爆贴热点`
- `write + lane=breakdown` -> `深度信号`

这样做的核心价值是：
- 不改 `信号快报` 结构
- 不改 `深度信号` 主链
- 只把“热点”作为一条独立内容语义接进现有 validate 流

## V1 Definition
### 爆贴热点是什么
一条高热帖子，加上最能代表争议和情绪焦点的评论，告诉用户：
- 这帖为什么火
- 大家主要在吵什么
- 这波关注点落在哪

### 爆贴热点不是什么
- 不是商机判断
- 不是需求验证
- 不是解决方案推荐
- 不是纯吐槽垃圾桶

## Input Rules
### 主要来源
V1 先主要吃 listing 帖，不碰 signal 的搜索主线：
- `hot:day`
- `rising:day`
- `top:day`
- `top:week`

### 入选规则
至少满足：
1. `listing_source` 来自 listing，而不是 search
2. `signal_level` 为 `hot` 或 `rising`
3. `score / num_comments` 达到高热阈值
4. 至少有 `2` 条可用 top comments
5. 评论区能看出明确争议点、关注点或观点分裂

### 禁入规则
以下内容不进 `爆贴热点`：
- 纯社区礼仪抱怨
- 纯标题党吐槽
- 纯 meme / 图梗
- 没有议题焦点的围观
- 已被质量闸门认定为低价值 meta complaint 的帖子

## Content Structure
`信号快报` 的详情结构不变。

`爆贴热点` 的详情结构在 V1 应该改成围绕“热帖讨论焦点”组织，而不是继续套 signal 的“值不值得追”结构。

建议最小详情结构：
1. `这帖为什么会火`
2. `大家主要在吵什么`
3. `最能代表这波讨论的两三种观点`
4. `原帖入口`

核心原则：
**热点卡讲“争议焦点”，信号卡讲“下一步价值”。**

## Workflow Fit
### 现有 skills
- `signal-ops`：继续使用，兼容 `lane=signal` 和 `lane=hot`
- `breakdown-ops`：不变，只管 `深度信号`

### 现有主链
- collect 不分叉
- review 时新增一个判断：
  - 这是 `信号快报`
  - 还是 `爆贴热点`

### V1 不做
- 不新增 `hot-ops`
- 不新增第三套 judge
- 不新增第三套 prompt 主链
- 不新增第三套 SOP 体系

## Success Criteria
满足以下条件，就算 V1 成立：

1. 用户在前台能明显区分：
   - `信号快报`
   - `爆贴热点`
   - `深度信号`

2. `爆贴热点` 不再像“换标签的 signal”

3. `信号快报` 的可信度不被热点内容污染

4. 现有 `signal-ops / breakdown-ops` 基本不需要推翻

## Risks
### 风险 1：爆贴热点继续长得像信号快报
Mitigation:
- 强制用 listing 帖
- 强制详情结构改成“讨论焦点”

### 风险 2：纯吐槽内容又混进来
Mitigation:
- 复用现有质量闸门
- 明确禁入 meta complaint / meme / pure venting

### 风险 3：内部 workflow 变复杂
Mitigation:
- V1 不做第三套系统
- 只做 lane，不改主链深度类型

## NOT in Scope
- 不修改当前 `信号快报` 的结构
- 不新增第三套 `card_type`
- 不重做 `breakdown-ops`
- 不在 V1 里做热点线专用 judge / prompt / skill
- 不把“爆贴热点”扩成完整独立产品系统
