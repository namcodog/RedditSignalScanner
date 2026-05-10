# Design: Card Skill Optimization Workflow
Date: 2026-04-07
Branch: main

## Problem Statement

当前卡片系统已经把前台合同、信号/拆解供给、topic-pack 路由和拆解 suggestion 基线拉起来了，但“怎么持续把卡片写得更好”还没有被工程化。

现在最大的风险不是模型不够强，而是：

- 还没有一套稳定的人类认可评判标准
- 失败样本还没有系统化沉淀成 failure taxonomy
- prompt / polish / rules 的优化还停留在人工局部修补

如果在这个阶段直接把整条卡片链交给自动优化，系统只会在没钉死的靶子上高效狂奔。

真正要解决的问题不是“怎么让 AI 更会写卡”，而是：

**怎么先建立一套卡片质量评估体系，再把优化工作安全地交给系统。**

## Premise Challenges

### 挑战 1：是不是应该直接优化整条卡片工作流？

不是。

整条工作流里混着：

- 采集质量
- 供给结构
- 卡片生成
- 人工评审
- 发布闸门

这些层一旦一起动，后面根本分不清：

- 是数据变好了
- 还是卡片 skill 变好了
- 还是只是门槛被放松了

结论：

**只优化 card skill，不优化整条卡片系统。**

### 挑战 2：是不是应该先做 autoresearch？

不是。

`autoresearch` 的前提是：

- eval set 已冻结
- judge 已校准
- keep / discard 标准已稳定

我们现在还没完成这些前提。

结论：

**先用 evals 工作流建立靶子，再让 autoresearch 上场。**

### 挑战 3：是不是信号卡和拆解卡应该一起优化？

不应该。

这两个任务不是一个任务：

- `📡 信号`：快、轻、判断前移
- `🔍 拆解`：慢、重、证据压缩

它们的样本结构、失败模式、评判标准都不一样。

结论：

**先只优化 signal skill，breakdown skill 后置。**

## Options Considered

| Option | What | Effort | Risk | Best for |
|---|---|---:|---:|---|
| A. 轻量人工版 | 继续人工读卡 + 手动改 prompt，不建正式 eval | S | 高 | 短期救火 |
| B. 标准版 | 先建 eval set + failure taxonomy + judge calibration，再用 autoresearch 优化 signal skill | M | 低 | 当前阶段，最稳 |
| C. 激进全自动版 | signal / breakdown 一起建自动优化闭环，直接推进整链 | L | 高 | 靶子已成熟后，远期 |

## Chosen Direction

选择 **B. 标准版**。

原因很直接：

1. 它和当前阶段匹配
   - 前台卡片合同已经稳定
   - 供给结构已基本收住
   - 现在正适合开始工程化“什么叫好卡”

2. 它能把“补丁式修卡”升级成“可复用优化系统”
   - 先建冻结样本
   - 再建人类对齐 judge
   - 最后才让系统循环试错

3. 它不污染生产链
   - 线上照常发卡
   - 优化链在离线环境里跑
   - 通过 canary 后才晋升

## Workflow Contract

### 1. 优化对象

当前只允许优化这 3 个面：

- `backend/app/services/hotpost/card_content_prompts.py`
- `backend/app/services/hotpost/card_content_polish.py`
- `backend/config/card_content_rules.yaml`

当前不允许作为“skill optimization”对象的内容：

- collect 规则
- topic-pack 路由
- breakdown suggestion 门槛
- publish 规则
- 前端展示文案

### 2. 工作流分层

#### 生产工作流

`collect -> candidates -> draft -> human review -> publish`

职责：

- 维持日常出卡
- 不承载 prompt 研究
- 不承载自动优化试错

#### 优化工作流

`frozen eval set -> human review -> failure taxonomy -> judge calibration -> autoresearch loop -> canary -> promote`

职责：

- 训练 card skill
- 只在离线评估链里反复试错
- 通过 canary 后再进生产

### 3. 标准版五步流程

#### Step 1: 建冻结 eval set

先建 `signal eval set v1`。

采样维度至少包含：

- `source_scope`
- `topic_pack`
- `intent_tags`
- `signal_level`
- 成功样本 / 坏样本

建议先只做 signal：

- 目标样本量：`40-60` 张
- 每周冻结一个版本，例如：`signal_eval_v1`

#### Step 2: 人工读卡建失败直觉

对冻结样本逐条人工阅读，不急着打分。

只记录：

- 哪张卡不行
- 具体哪里不行
- 为什么不行

禁止直接跳到 prompt 修改。

#### Step 3: 归纳 failure taxonomy

把坏卡归纳成可重复识别的失败模式。

Signal 卡建议优先归这几类：

- `只是在转述 Reddit`
- `没有明确判断增量`
- `audience 不是“谁在聊”`
- `why_now 没回答“为什么现在值得看”`
- `标题像报告，不像线索`
- `证据明明不够，却写得像结论`

#### Step 4: 写 judge + 校准 judge

先写两层 judge：

- 字段级 judge
  - title
  - summary_line
  - audience
  - why_now
- 整卡级 judge
  - 这张卡是否完成“判断前移”

然后做人工对齐：

- 人先打 `15-20` 条
- judge 再打同一批
- 如果 judge 和人不一致：
  - 改 judge
  - 不改 prompt

这一步完成前，不允许上 autoresearch。

#### Step 5: 启动 autoresearch 式优化

只在下面条件同时满足后开启：

- eval set 冻结
- judge 校准完成
- 优化对象收窄到 signal skill

循环规则：

`改 prompt/rules -> 跑 frozen eval set -> judge 打分 -> keep/discard`

保留条件：

- 总分提升
- 关键字段分不退步
- 复杂度没有明显上升

### 4. 产物清单

标准版第一阶段应产出：

- `signal_eval_v1.jsonl` 或等价结构化样本集
- `signal_failure_taxonomy.md`
- `signal_judge_prompt.md`
- `signal_judge_calibration.md`
- `card_skill_results.tsv`

### 5. 发布门槛

优化结果不能直接替换生产。

必须经过：

`offline eval pass -> canary batch -> human check -> promote`

canary 规模建议：

- `5-10` 张 signal 卡

通过标准：

- judge 分数优于基线
- 人工抽检不出现新型明显退化

## Success Criteria

这个工作流是否成功，不看“模型是不是更高级”，只看下面 5 条：

1. 能稳定复现“为什么这张卡是坏卡”
2. 人工和 judge 的判断能明显对齐
3. signal skill 的优化不再靠人工逐张抠
4. 优化结果能通过 canary 再进生产
5. 每轮优化都能明确回答：
   - 改了什么
   - 为什么保留
   - 为什么回滚

## Risks

### 风险 1：一上来把 breakdown 也拉进来

后果：

- 样本太少
- judge 难校准
- 流程复杂度爆炸

缓解：

- 第一阶段只做 signal

### 风险 2：judge 看起来能用，其实没对齐人类判断

后果：

- 自动优化继续在错靶子上狂奔

缓解：

- 必须先做人工对齐
- judge 不对齐就不准启动 autoresearch

### 风险 3：把生产链和优化链混在一起

后果：

- 分不清是供给变了还是 skill 变了
- 很难回滚

缓解：

- 生产链和优化链分层运行
- 离线通过后再 canary

## NOT in Scope

当前明确不在范围内的内容：

- 优化 breakdown skill
- 自动发布拆解卡
- collect/topic-pack 再重构
- 线上实时 A/B 全量试验
- 用机器自动生成 eval 标准

## Next Action

下一步不是改 prompt，而是先做：

1. 建 `signal eval set v1`
2. 拉一轮人工 error analysis
3. 产出 `signal failure taxonomy v1`

这三步做完，才有资格进入 judge 和 autoresearch。
