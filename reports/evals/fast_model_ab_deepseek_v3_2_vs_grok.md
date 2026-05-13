# fast_model A/B：DeepSeek V3.2 vs Grok 4.1 Fast

## 范围
- 对象：`signal / validate` 生成
- 模型：
  - A：`x-ai/grok-4.1-fast`
  - B：`deepseek/deepseek-v3.2`
- 固定条件：
  - 同一批真实候选
  - `HOTPOST_REASONING_ENABLED=0`
  - 不写回生产

## 样本
1. `cand-ai-automation-1sfnauw` `upstream-winds`
2. `cand-ai-automation-1sd78l0` `agent-builder`
3. `cand-ecommerce-sellers-1s9m07l` `selection-signals`
4. `cand-business-growth-ops-1sbnkdt` `paid-economics`

原始输出 JSON：
- [fast_model_ab_deepseek_v3_2_vs_grok.json](/Users/hujia/Desktop/RedditSignalScanner/reports/evals/fast_model_ab_deepseek_v3_2_vs_grok.json)

## 结果

### 1. upstream-winds
- Grok：
  - 标题更短更直接，但残留 `cyber model / rollout`
  - `summary_line` 仍有明显 Reddit 转述腔和英文原话
- DeepSeek：
  - 能更完整地把“能力更强 + 邀请制 + 商业排他性”串成一个解释
  - 但写法更像“复述讨论全文”，不够前台化

判断：
- 语义理解：`DeepSeek V3.2` 更完整
- 前台读感：两者都不理想，`DeepSeek` 更重，`Grok` 更散

### 2. agent-builder
- 两边输出完全一致
- 原因不是两个模型能力完全相同，而是：
  - 当前 `agent-builder` 有较强 pack override
  - 模型差异被后处理基本抹平

判断：
- 这类成熟 pack 现在换 fast_model，收益很小

### 3. selection-signals
- 两边输出完全一致
- 同样说明：
  - `selection-signals` 的 pack 级写法已经很强
  - 模型差异很难在最终前台文案里体现

判断：
- 这类 pack 不值得为“语义理解”全量换 fast llm

### 4. paid-economics
- Grok：
  - 更像“知道问题在哪，但直接把后台词全喷出来”
  - `gclid decode error / cookie / hidden field / smart bidding` 太工程化
- DeepSeek：
  - 因果关系解释更完整
  - 至少把“为什么回传失败会带偏智能出价”说清了
  - 但仍残留 `GCLID / Google 智能出价` 等专业词

判断：
- 语义理解：`DeepSeek V3.2` 略好
- 客户端表达：仍然需要 polish，人话化没有自动解决

## 速度
- `upstream-winds`
  - Grok：`12.76s`
  - DeepSeek：`17.29s`
- `agent-builder`
  - Grok：`11.07s`
  - DeepSeek：`14.84s`
- `selection-signals`
  - Grok：`10.93s`
  - DeepSeek：`6.95s`
- `paid-economics`
  - Grok：`16.00s`
  - DeepSeek：`13.51s`

结论：
- DeepSeek 不是稳定更慢，但整体没有形成明显的速度优势
- 当前证据不足以支持“因为更快而替换”

## 结论
- 如果优先级是**语义理解**：
  - 在 `upstream-winds`、`paid-economics` 这种 override 较弱、需要自己整合长帖语义的场景，`DeepSeek V3.2` 更有潜力
- 如果优先级是**当前小程序前台最终效果**：
  - `DeepSeek V3.2` 没有稳定赢
  - 因为很多成熟 pack 已经被 override / polish 拉平
- 当前最合理的决定不是：
  - 直接全量替换 `fast_model`
- 当前更合理的决定是：
  - 继续保留 `x-ai/grok-4.1-fast` 作为默认 `fast_model`
  - 如果要进一步用 DeepSeek，先只在：
    - 弱 override 的 pack
    - 或离线 lab / 更窄 pack canary
    做定向试点
