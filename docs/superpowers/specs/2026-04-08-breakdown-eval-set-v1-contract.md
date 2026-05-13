# Design: Breakdown Eval Set V1
Date: 2026-04-08
Branch: current workspace

## Problem Statement

`breakdown V2` 主链已经跑通：

`suggestion -> auto write draft -> human review -> publish`

但现在还缺一块真正的地基：

**还没有一套冻结、可重复、专门评估 `🔍 拆解` 质量的 `breakdown eval set`。**

没有它，后面这些事都不稳：

- 人工 review 只能靠临场感觉
- thesis 好不好、quote_pack 够不够支撑，没法稳定比较
- `breakdown judge` 会漂
- 后续 canary / promote 会变成移动靶子

所以这一步要解决的，不是“多做一些拆解卡”，而是：

**定义一套能稳定代表拆解卡成败面的评估样本合同。**

## Premise Challenges

### 挑战 1：能不能直接拿已发布 `write` 卡当 eval set？

不能。

原因：

1. 当前真实 `write` 样本数量还不大
2. 已发布卡天然偏“已经过人审”，坏样本不够
3. 如果只拿已发布卡，系统只会学会模仿“能发出去的样子”，学不会识别“看着深，其实没新判断”的坏拆解

结论：

**不能只用 published write。必须用混合样本。**

### 挑战 2：能不能大量用 synthetic 把拆解样本补满？

也不能。

拆解卡最核心的问题不是“句子像不像人话”，而是：

- thesis 到底是不是由多条证据共同指向
- quote_pack 有没有真的支撑结论
- 这张卡是不是把几个相关 signal 硬拼成一个假判断

这些病，机器自己编的 synthetic 样本很容易编不出真实共指关系。

结论：

**V1 必须 real-first，synthetic 只补边。**

### 挑战 3：eval unit 应该只看成品卡吗？

不能只看成品。

因为我们优化的不是纯文案，而是：

- 给定一组 grouped candidates
- 给定 suggestion hypothesis
- 生成一张 breakdown 卡

如果只看最终卡片，不看输入，就无法判断：

- thesis 是不是脑补
- quote_pack 是不是在强行支撑
- 同一个 grouped bundle 到底值不值得升 breakdown

结论：

**eval unit = grouped input bundle + breakdown 输出 + 人工标注。**

## Options Considered

| Option | What | Effort | Risk | Best for |
|---|---|---:|---:|---|
| A. Published-only | 只拿已发布 write 卡做评估集 | S | 高 | 快，但会失真 |
| B. Mixed real-first | 真实 grouped sample 为主，少量 synthetic 补边 | M | 低 | 当前阶段，最稳 |
| C. Synthetic-first | 先批量编 grouped sample，再少量人工校准 | M | 高 | 样本极少时的临时权宜 |

## Chosen Direction

选择 **B. Mixed real-first**。

原因：

1. 能保留真实 Reddit 多帖证据质感
2. 能覆盖“看起来像拆解、其实不成立”的坏样本
3. 又能用少量 synthetic 补足边角和极端弱例

## Eval Set Contract

### 1. 优化范围

`breakdown eval set v1` 只服务于：

- `card_type = write`
- `breakdown content quality optimization`

当前不纳入：

- signal 卡
- suggestion 门槛优化
- breakdown supply 规则
- materialize 主链
- publish 闸门

### 2. Eval Unit 定义

每条 eval case 必须同时包含 3 层：

#### A. 输入层

- `source_scope_id`
- `topic_pack_id`
- `suggestion_id`（如果有）
- `candidate_ids`
- `thread_count`
- `community_count`
- `intent_tags`
- `hypothesis`
- `reason_codes`
- `evidence_quotes`
- `source_communities`

#### B. 输出层

- `title`
- `summary_line`
- `audience`
- `why_now`
- `detail.thesis`
- `detail.writing_angle_or_perspective`
- `detail.tension_point_or_why_it_matters`
- `detail.quote_pack`

#### C. 标注层

- `overall_pass`
- `field_passes`
- `failure_tags`
- `review_notes`

也就是说：

**一条 breakdown eval case 不是“这张深度卡长什么样”，而是“给这包 grouped evidence，系统写出了什么，人怎么判”。**

### 3. 样本来源

V1 采用混合来源：

#### 真实样本（主）

占比：**75%-85%**

来源包括：

- 已 materialize 的真实 `write draft`
- 已发布 `write` 卡
- suggestion 进入 write draft 但被人判定“不该发”的样本

#### synthetic 样本（辅）

占比：**15%-25%**

只用于补足这些边角：

- 多帖但 thesis 明显站不住
- quote_pack 看起来多，但其实共指关系很弱
- 同 pack、同对象、不同判断方向的冲突样本
- 容易把“共现”误写成“共因”的样本

### 4. 样本量

`breakdown eval set v1` 目标样本量：

- **24 条**

这是 V1 最稳的量：

- 不太少，够做 failure taxonomy
- 也不太大，人工真能一轮读完
- 不会逼着系统为了凑数造太多假样本

建议结构：

- `18` 条真实样本
- `6` 条 synthetic 边角样本

### 5. 样本优先级

V1 先只覆盖当前最有土壤的两条 pack：

1. `selection-signals`
2. `agent-builder`

原因：

- 这两条是当前最成熟、最适合做 breakdown 的信号主战场
- 不把样本盘子摊到所有 pack，能避免 V1 失焦

### 6. 采样维度

V1 至少按这 6 个维度覆盖：

1. `topic_pack`
   - `selection-signals`
   - `agent-builder`

2. `evidence shape`
   - `2 threads / 1 community`
   - `2 threads / 2 communities`
   - `3 threads / 2+ communities`

3. `hypothesis quality`
   - 明显成立
   - 边界成立
   - 明显不成立

4. `quote support`
   - quote_pack 真支撑 thesis
   - quote_pack 部分支撑
   - quote_pack 只是看起来热闹

5. `case polarity`
   - 好样本
   - 坏样本
   - 边界样本

6. `decision tension`
   - 买不买 / 选不选
   - 用不用 / 信不信
   - 能不能落地 / 值不值得继续追

### 7. 配额规则

V1 不追求完美均匀，但必须满足底线：

- `selection-signals` 至少 `10` 条
- `agent-builder` 至少 `8` 条
- 明显坏样本至少 `6` 条
- 边界样本至少 `6` 条
- 至少 `8` 条样本满足 `2 communities` 或 `3 threads`

这里最关键的一条：

**V1 必须故意保留“看起来像拆解，其实不成立”的坏样本。**

### 8. 存储格式

V1 建议分成两个文件：

#### 样本主文件

- `reports/evals/breakdown_eval_set_v1.jsonl`

每行一条 case，包含：

- `input_bundle`
- `baseline_output`
- `metadata`

#### 标注文件

- `reports/evals/breakdown_eval_labels_v1.jsonl`

每行一条人工评审结果，包含：

- `eval_case_id`
- `overall_pass`
- `field_passes`
- `failure_tags`
- `review_notes`

### 9. Failure Tags（V1 初始集）

V1 先锁这一组，不追求太多：

- `weak_thesis`
- `quote_pack_not_supporting_claim`
- `no_judgment_gain`
- `reddit_restatement`
- `why_now_not_actionable`
- `audience_not_who_is_talking`
- `stitched_not_coherent`
- `reporty_title`

其中最关键的 3 个是：

1. `weak_thesis`
2. `quote_pack_not_supporting_claim`
3. `stitched_not_coherent`

因为这 3 个最能代表“拆解卡特有的失败方式”。

### 10. Build 顺序

V1 严格按这个顺序：

1. 导出真实 `write` 样本
2. 人工筛掉 lineage 不完整样本
3. 再补 `6` 条 synthetic 边角样本
4. 冻结 `breakdown_eval_set_v1`
5. 再进入 human review / taxonomy / judge

## Success Criteria

只要满足下面 5 条，就算 `breakdown eval set v1` 建成：

1. 成功导出 `24` 条样本
2. 每条样本都包含 grouped input + breakdown output + label slot
3. 两个主战场 pack 都有覆盖
4. 坏样本和边界样本都占到足够比例
5. 样本冻结后，可以直接进入人工 review

## Risks

### 风险 1：样本太少，最后全靠 synthetic 凑

缓解：

- 先只做 `24` 条
- 先只覆盖两条 pack
- 不够就降范围，不降真实性

### 风险 2：把 breakdown 的问题偷换成 signal 的问题

缓解：

- failure tags 先锁拆解特有问题
- 不把 `signal judge` 直接拿来复用

### 风险 3：为了做 eval set，反向改主链

缓解：

- eval set 构建只读现有样本
- 不在这一步改 materialize / suggestion / publish

## NOT in Scope

- 不做 breakdown judge v1
- 不做 breakdown canary
- 不做 breakdown prompt 优化
- 不做新的 breakdown supply 改造
- 不做前端或产品层改动
