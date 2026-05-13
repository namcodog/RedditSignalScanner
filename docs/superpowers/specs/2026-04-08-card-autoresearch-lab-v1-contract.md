# Contract: Card Autoresearch Lab V1
Date: 2026-04-08
Branch: current workspace

## 一句话目标

把我们已经手工跑通的 `eval -> judge -> canary -> promote`，升级成一个**轻量、离线、受控**的卡片优化实验室，用来更快地优化卡片写法，但**不碰生产主链**。

## 为什么现在值得做

当前小程序的主链已经够稳：

- `📡 信号` 有稳定供给
- `🔍 拆解` 主链已跑通
- `signal / breakdown judge` 已可用
- 多个成熟 pack 已经验证过 `keep / discard -> promote`

现在最值钱的不是再补新功能，而是：

**把“手工试 prompt 变体”升级成一个更快、更可控的离线实验循环。**

## 当前判断

### 我们已经有的

- 冻结 eval set
- human review
- failure taxonomy
- judge calibration
- canary
- promote

### 我们还没有的

- 自动生成变体
- 自动批量试验
- 自动 keep / discard 排行

所以 V1 的正确形态不是“全自动优化引擎”，而是：

**一个受控的 autoresearch 实验室。**

## Scope

V1 只允许优化这 3 类文件：

1. `backend/app/services/hotpost/card_content_prompts.py`
2. `backend/app/services/hotpost/card_content_polish.py`
3. `backend/config/card_content_rules.yaml`

但三者优先级不同：

### 第一优先级
- `card_content_prompts.py`

### 第二优先级
- `card_content_polish.py`

### 第三优先级
- `card_content_rules.yaml`
  - 只允许动软规则：
    - negative examples
    - 禁用句型
    - 轻量风格约束

## Not in Scope

V1 明确不碰这些：

- collect / source scope / topic-pack 供给
- signal input quality gate
- breakdown suggestion 门槛
- auto materialize 机制
- publish 逻辑
- judge 定义本身
- 前端文案和交互
- 数据库结构

## 实验对象顺序

### Phase 1
先只做：
- `signal` 的 prompt 层优化

### Phase 2
再做：
- `breakdown` 的 prompt 层优化

### Phase 3
最后才考虑：
- `polish`
- `rules.yaml` 的软规则

## 工作流

### 输入

- frozen eval set
- 当前 judge
- 当前生产基线
- 待试验变体集合

### 循环

1. 生成少量变体
2. 在冻结 eval set 上跑全量
3. 用现有 judge 打分
4. 输出 keep / discard 排名
5. 人工复核 top diff
6. 只有胜出变体，才进入 canary
7. canary 胜出后才允许 promote

## 运行边界

### 自动化能做到哪里

- 自动生成变体
- 自动离线跑分
- 自动生成 keep / discard 结果

### 自动化不能做到哪里

- 不能自动改生产文件
- 不能自动 promote
- 不能自动上线
- 不能自动决定优化目标

## 成功标准

V1 做完，至少满足：

1. 可以对 `signal` prompt 跑一轮真正的 autoresearch 式实验
2. 可以输出可读的 keep / discard 结果
3. 可以把胜出变体送入 canary
4. 整个过程不污染生产主链
5. 人能解释为什么保留这个变体，而不是“模型自己觉得好”

## 失败标准

出现下面任一情况，就算 V1 跑偏：

1. 同时动 prompt + collect + gate
2. judge 本身也被自动改掉
3. 直接自动 promote 到生产
4. 变体太多，人工已经看不懂 keep / discard 理由
5. pass rate 提升了，但文风明显变怪或过拟合 judge

## 当前最小执行计划

1. 建 `card-autoresearch-lab` runner
2. 先接 `signal` 的 prompt 变体搜索
3. 复用现有：
   - `signal eval set`
   - `signal judge`
   - `canary`
4. 第一轮只回答一个问题：
   - 能不能比当前基线更稳定地降低：
     - `reddit_restatement`
     - `no_judgment_gain`
     - `why_now_not_actionable`

## 最终定位

这不是一个新主链。

这是一个：

**只服务于卡片质量优化的离线实验室。**

它的职责是：

**加速试错。**

不是：

**替代判断。**
