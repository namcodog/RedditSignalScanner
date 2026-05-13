# Design: Signal Eval Set V1
Date: 2026-04-07
Branch: main

## Problem Statement

当前我们已经决定走 `card skill optimization` 标准版：

`frozen eval set -> human review -> failure taxonomy -> judge calibration -> autoresearch loop -> canary -> promote`

但这条链现在还缺第一块地基：

**还没有一套冻结、可重复、能代表真实业务质量的 `signal eval set`。**

没有它，后面这些事都做不稳：

- error analysis 会变成随手抓样本
- judge calibration 会飘
- autoresearch 会在移动靶子上优化

所以这一步要解决的，不是“多收集一些卡”，而是：

**定义一套能稳定代表 signal 卡真实成败面的评估样本合同。**

## Premise Challenges

### 挑战 1：能不能直接拿现有 published signal 卡当 eval set？

不能。

原因有两个：

1. 当前 `published_validate = 16`，量不够
2. 已发布卡天然偏“已经过审”，坏样本不够，边缘样本也不够

如果只拿已发布卡，后面会学出一种假象：

- 系统只学会“模仿现在能发出去的卡”
- 但学不会识别那些“看起来像样、其实没价值”的坏卡

结论：

**不能只用 published。必须用混合样本集。**

### 挑战 2：能不能先大量用 synthetic data 把样本补满？

也不能。

synthetic data 可以补边，但不能当主体。

原因很硬：

- 卡片失败很多时候不是“语言问题”
- 而是“证据强度不够”“判断没前移”“看起来像在说 Reddit 而不是在说你”

这些病，机器自己编的样本很容易编不出真实质感。

结论：

**V1 必须是 real-first，synthetic-second。**

### 挑战 3：eval unit 应该是“最终卡片文案”还是“输入+输出整包”？

必须是整包。

因为我们优化的不是纯文案，而是：

- 给定 evidence bundle
- 生成一张 signal 卡

如果只看最终卡片，不看输入证据，就无法判断：

- 卡片有没有脑补
- 卡片有没有把弱证据写成强结论
- 卡片有没有辜负输入里的真信息

结论：

**eval unit = 输入 bundle + 生成结果 + 人工标注，不是单独一段成品文案。**

## Options Considered

| Option | What | Effort | Risk | Best for |
|---|---|---:|---:|---|
| A. Published-only | 只拿已发布 signal 卡做评估集 | S | 高 | 快，但会失真 |
| B. Mixed real-first | 真实样本为主，结构化 synthetic 补边 | M | 低 | 当前阶段，最稳 |
| C. Synthetic-first | 先用维度生成大量 synthetic bundle，再少量人工校准 | M | 高 | 数据极缺时才勉强可用 |

## Chosen Direction

选择 **B. Mixed real-first**。

原因：

1. 它能覆盖真实坏样本
2. 它能保留真实 Reddit 证据质感
3. 它又能用少量 synthetic 把边角补齐

## Eval Set Contract

### 1. 优化范围

`signal eval set v1` 只服务于：

- `card_type = validate`

当前不纳入：

- `write / 拆解卡`
- breakdown suggestion
- collect / topic-pack / publish 规则

### 2. Eval Unit 定义

每条 eval case 必须同时包含 3 层：

#### A. 输入层

- `source_scope_id`
- `topic_pack_id`
- `signal_level`
- `why_now_reason`
- `intent_tags`
- `thread_count`
- `community_count`
- `quote_count`
- `source_communities`
- `evidence_quotes`

#### B. 输出层

- `title`
- `summary_line`
- `audience`
- `why_now`
- `detail`

#### C. 标注层

- `overall_pass`
- `field_passes`
- `failure_tags`
- `review_notes`

也就是说：

**一条 eval case 不是“这张卡长什么样”，而是“给这包证据，系统写出了什么，人怎么判”。**

### 3. 样本来源

V1 采用混合来源：

#### 真实样本（主）

占比：**70%-80%**

来源包括：

- 已发布 `validate` 卡
- 当前 candidate -> draft 链里的真实样本
- 曾经被人工否掉、或看起来能发但后面被判定为不够好的卡

#### synthetic 样本（辅）

占比：**20%-30%**

只用于补足这些边角：

- 极弱证据但语气容易写重
- 高意图但样本稀薄
- 同一 scope 下少见 topic-pack
- 容易出“Reddit 转述腔”的输入组合

### 4. 样本量

`signal eval set v1` 目标样本量：

- **48 条**

这是第一版最稳的量：

- 不太少，够做失败分类
- 也不太大，人工能读完

建议结构：

- `36` 条真实样本
- `12` 条 synthetic 补边样本

### 5. 采样维度

V1 至少按这 6 个维度覆盖：

1. `source_scope`
   - `ai-automation`
   - `ecommerce-sellers`
   - `business-growth-ops`

2. `topic_pack`
   - 每个活跃 pack 至少有基础覆盖

3. `signal_level`
   - `hot / rising / sustained`

4. `intent heat`
   - 高：`替换 / 求推荐 / 明确阻塞`
   - 中：`避坑`
   - 低：`趋势变化`

5. `evidence strength`
   - 弱：`1 thread / 1 community / 2 quotes`
   - 中：`2 threads or 3 quotes`
   - 强：`2 communities or 3 threads`

6. `case polarity`
   - 好样本
   - 坏样本
   - 边界样本

### 6. 配额规则

V1 不追求完美均匀，但必须满足底线：

- 每个 `source_scope` 至少 `12` 条
- 每个活跃 `topic_pack` 至少 `4` 条
- 高/中/低 intent 都要有
- 弱证据样本至少 `10` 条
- 明显坏样本至少 `12` 条

这里最关键的一条：

**V1 必须故意保留弱样本和烂样本，不准只收“看起来像样”的卡。**

### 7. 存储格式

V1 建议分成两个文件：

#### 样本主文件

- `reports/evals/signal_eval_set_v1.jsonl`

每行一条 case，包含：

- `input_bundle`
- `baseline_output`
- `metadata`

#### 标注文件

- `reports/evals/signal_eval_labels_v1.jsonl`

每行一条人工评审结果，包含：

- `eval_case_id`
- `overall_pass`
- `field_passes`
- `failure_tags`
- `review_notes`

这样做的原因：

- 样本和标注分离
- 后面 judge calibration 不会改坏原始样本

### 8. 评审规则

人工评审阶段先不用复杂分数。

V1 统一用：

- **字段级 pass/fail**
- **整卡级 pass/fail**

不建议上 1-5 分量表。

字段级至少评这 4 项：

- `title`
- `summary_line`
- `audience`
- `why_now`

整卡级只判断一件事：

**这张卡有没有完成“判断前移”，还是只是在转述 Reddit。**

### 9. Failure Tags 初版骨架

V1 先锁这批 failure tags：

- `reddit_restatement`
- `no_judgment_gain`
- `audience_not_who_is_talking`
- `why_now_not_actionable`
- `reporty_title`
- `evidence_overclaim`
- `generic_copy`
- `quote_not_used_well`

后面 error analysis 可以再扩，但 V1 先用这套骨架起步。

### 10. 冻结规则

`signal_eval_set_v1` 一旦冻结：

- 不再随手加减样本
- 不再因为某轮 prompt 不适配而临时改样本

只有在这些情况下才允许出 `v2`：

- 活跃 topic-pack 结构明显变化
- failure taxonomy 发生重大扩展
- judge 校准阶段发现 v1 样本面不够

## Mapping to Evals-Skills

这套合同和 `evals-skills` 的映射关系是：

- `generate-synthetic-data`
  - 用于补 12 条 synthetic 边角样本

- `error-analysis`
  - 用于读冻结样本，建立 failure taxonomy

- `write-judge-prompt`
  - 用于写字段级 / 整卡级 judge

- `validate-evaluator`
  - 用于做人类打分和 judge 的对齐校准

当前不需要用：

- `evaluate-rag`
- `build-review-interface`

它们是后续增强项，不是 V1 必需项。

## Success Criteria

`signal eval set v1` 做完之后，至少要满足这 5 条：

1. 不依赖临时挑卡，也能稳定复现同一批评估样本
2. 真实样本占主体，不是 synthetic 伪世界
3. 坏样本、边界样本都有，不是清一色“看起来差不多不错”
4. 人工读一轮之后，能稳定归纳出 failure taxonomy
5. 后续 judge 和 autoresearch 都能以它为固定地基

## Risks

### 风险 1：样本太偏“已发布好卡”

后果：

- judge 只能学会模仿现状
- 学不会识别假好卡

缓解：

- 明确保留坏样本和弱样本

### 风险 2：synthetic 比例太高

后果：

- eval 看起来完整
- 但和真实 Reddit 证据脱节

缓解：

- synthetic 上限锁在 `30%`

### 风险 3：评审一上来用复杂打分表

后果：

- 人工对齐变慢
- judge 难校准

缓解：

- V1 只用 pass/fail

## NOT in Scope

当前明确不在 `signal eval set v1` 范围内：

- breakdown eval set
- 自动生成 judge
- 线上 AB 实验
- prompt 自动优化
- collect/topic-pack 再改造

## Next Action

这份合同锁定后，下一步直接做：

1. 拉出 `36` 条真实 signal 样本候选
2. 按维度补 `12` 条 synthetic 边角样本
3. 产出 `signal_eval_set_v1.jsonl`

这一步完成后，才能进入人工 error analysis。
