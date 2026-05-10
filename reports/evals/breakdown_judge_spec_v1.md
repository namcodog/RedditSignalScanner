# Breakdown Judge Spec V1

## 目标

这份 judge spec 只服务于 `🔍 拆解`，不用来评 `📡 信号`。

judge 的任务不是挑文风喜好，而是判断：

**给定 grouped evidence 和当前拆解卡输出，这张卡有没有提出一个成立的更深判断，并且真的被 quote 支撑。**

## 输入

每条 case 都必须同时看：

- `input_bundle`
- `baseline_output`

禁止只看成品卡，不看 grouped 输入。

## 输出

judge 先只产出两层结果：

- 字段级 `pass/fail`
  - `title`
  - `summary_line`
  - `audience`
  - `why_now`
  - `thesis`
  - `quote_pack`
- 整卡级 `overall_pass/fail`

另外必须返回：

- `failure_tags`
- `review_notes`

## 字段级标准

### 1. `title`

`pass` 条件：

- 能说出这张拆解卡真正压出的判断冲突
- 不是论坛条目，也不是研究报告标题
- 没把弱共指写成强结论

常见失败：

- `reporty_title`
- `stitched_not_coherent`

### 2. `summary_line`

`pass` 条件：

- 不是把几条帖子压成一段转述
- 能直接把读者带到“真正卡点”上
- 有判断增量，不只是换种说法复述现象

常见失败：

- `reddit_restatement`
- `no_judgment_gain`

### 3. `audience`

`pass` 条件：

- 写的是 Reddit 上真实在聊这件事的人
- 不是目标 persona，也不是过度外推的业务角色

常见失败：

- `audience_not_who_is_talking`

### 4. `why_now`

`pass` 条件：

- 回答了为什么这波 grouped discussion 现在值得看
- 能帮助用户判断“继续追 or 划走”
- 不只是模板化时间句

常见失败：

- `why_now_not_actionable`

### 5. `thesis`

`pass` 条件：

- 有明确的更深一层判断
- 不是把多个 signal 硬拼成一句漂亮话
- 这个判断能从 quote_pack 看出共指关系

常见失败：

- `weak_thesis`
- `stitched_not_coherent`

### 6. `quote_pack`

`pass` 条件：

- 至少能明显支撑 thesis
- 引用之间不是同义反复，也不是热闹堆砌
- 不混入 bot / 自动回复 / 无信息价值原话

常见失败：

- `quote_pack_not_supporting_claim`
- `reddit_restatement`

## 整卡级标准

`overall_pass` 只有在下面同时成立时才通过：

1. thesis 成立
2. quote_pack 真的支撑 thesis
3. 整卡有判断增量，不只是深度感表演

下面任一明显成立，整卡直接 `fail`：

- `weak_thesis`
- `quote_pack_not_supporting_claim`
- `stitched_not_coherent`
- `no_judgment_gain`

## Failure Tags 使用约束

- 一张卡可以挂多个 tag
- 但只挂最主要的 `1-3` 个
- 先挂结构性失败，再挂字段性失败

优先级建议：

1. 结构性失败
   - `weak_thesis`
   - `quote_pack_not_supporting_claim`
   - `stitched_not_coherent`
   - `no_judgment_gain`
2. 字段性失败
   - `reddit_restatement`
   - `why_now_not_actionable`
   - `audience_not_who_is_talking`
   - `reporty_title`

## 暂不做的事

- 不上 1-5 分量表
- 不让 judge 直接改写拆解卡
- 不把 judge 接到 publish 闸门

judge 在当前阶段只做一件事：

**稳定判断一张拆解卡是不是成立。**
