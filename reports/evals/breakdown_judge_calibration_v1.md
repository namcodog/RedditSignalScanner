# Breakdown Judge Calibration V1

## 批次说明

- 批次：`v1`
- 样本量：`18`
- 结构：`14 pass / 4 fail`
- 来源：创始人人工判定

这轮校准先钉住 3 条最容易跑偏的边界：

- suggestion 来源的卡，什么时候是“硬拼”
- thesis 看起来顺，但其实太泛、太抽象
- 单卡能成立，但放到卡组里已经没有新增判断时，怎么判 `no_judgment_gain`

## 本轮人工判定暴露出的边界

### 1. `suggestion_write` 要默认更严格

当前两条 suggestion case 都被判 fail，不是因为它们“不够长”，而是因为：

- 候选不在同一个决策问题上
- thesis 抽象到换任何品类都能成立
- quote_pack 没有形成真正共指

所以 judge 看到 suggestion 来源时，必须优先审：

- 是不是同一个对象
- 是不是同一个决策张力
- thesis 有没有被抽象成万能句

### 2. `stitched_not_coherent` 不只用于“明显不相关”

它还有第二种命中方式：

- 主题看着相近
- 但这张卡没有独立判断增量
- 本质上只是把一条已经成立的 common trope 换个说法再写一遍

这也是为什么：

- `roadmap-lightweight-alignment`
- `sales-followup-slip`

会被人工判 fail。

### 3. `weak_thesis` 的重点不是“浅”，而是“泛”

真正的问题不是 thesis 不够花哨，而是：

- 这句 thesis 换到别的场景也成立
- 它不是这组证据特有的判断

典型就是：

- `breakdown-eval-suggestion-suggestion-ecommerce-sellers-258155f585`

### 4. `reporty_title` 不是文风小毛病

在拆解卡里，标题一旦像白皮书、分析报告、行业条目，
往往对应的不是单纯风格问题，而是：

- 这张卡已经失去信号张力
- 或者 thesis 本身没有独立判断增量

## 对 judge 的直接约束

judge v2 必须优先学会这 4 件事：

1. suggestion 来源默认从严，不轻易放过“抽象但不共指”的 thesis
2. thesis 只要“换个品类也成立”，优先挂 `weak_thesis`
3. 当卡只是在重复已有套路，而没有新的判断推进时，可以挂 `no_judgment_gain`
4. 标题像白皮书时，不要只当文风问题；要联动检查 thesis 是否也在报告化

## 当前结论

breakdown judge v1 的主问题，不是不会看强 thesis，
而是对下面两类 fail 还不够敏感：

- `suggestion_write` 的硬拼
- `published_write` 里的冗余套路化拆解

下一步应直接写：

- `breakdown_judge_prompt_v2`

然后再跑一轮 full eval 对比。
