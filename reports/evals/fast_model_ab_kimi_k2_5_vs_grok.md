# fast_model A/B：Kimi K2.5 vs Grok 4.1 Fast

## 范围
- 对象：`signal / validate` 生成
- 模型：
  - A：`x-ai/grok-4.1-fast`
  - B：`moonshotai/kimi-k2.5`
- 固定条件：
  - 同一批真实候选
  - `HOTPOST_REASONING_ENABLED=0`
  - 不写回生产

## 先决检查
- `moonshotai/kimi-k2.5` 在 OpenRouter 上模型名存在
- 用当前 key 做最小 `json_object` 测试：
  - 可连
  - 返回成功
  - 约 `12.46s`

## 样本
1. `cand-ai-automation-1sfnauw` `upstream-winds`
2. `cand-ai-automation-1sd78l0` `agent-builder`
3. `cand-ecommerce-sellers-1s9m07l` `selection-signals`
4. `cand-business-growth-ops-1sbnkdt` `paid-economics`

## 结果

### 1. upstream-winds
- Grok：
  - `13.56s`
  - 偏论坛转述，但还能产出 JSON
- Kimi：
  - `39.69s`
  - 语义更完整，能把“安全动机 + 商业动机”都说出来
  - 但仍偏“解释讨论”，没有自动变成更利索的前台判断句

判断：
- 语义理解：`Kimi K2.5` 略好
- 前台读感：没有稳定赢
- 速度：明显更慢

### 2. agent-builder
- Grok：
  - `11.80s`
- Kimi：
  - `30.74s`
- 两边最终输出基本一致

判断：
- 成熟 pack 上，差异被 override 基本抹平
- Kimi 没有带来可见增益，只带来更高延迟

### 3. selection-signals
- Grok：
  - 正常返回
- Kimi：
  - `LLM returned invalid JSON`
  - 原始返回为空

判断：
- 当前主链下存在结构化输出稳定性风险

### 4. paid-economics
- Grok：
  - `14.22s`
  - 正常返回
- Kimi：
  - `LLM returned invalid JSON`
  - 原始返回为空

判断：
- 当前主链下存在结构化输出稳定性风险

## 结论
- 如果只看个别弱 override 场景的语义完整度：
  - `Kimi K2.5` 有潜力
- 但如果看当前 `fast_model` 的真实职责：
  - 稳定 JSON
  - 快速出卡
  - 最终前台可读性
- 当前证据不支持切换，原因有两条：
  1. **稳定性不够**
     - 在 `selection-signals`
     - 在 `paid-economics`
     - 都出现了真实 `invalid JSON`
  2. **延迟明显偏高**
     - 在已有成功样本上，普遍慢于当前 `fast_model`

## 最终判断
- 当前**不建议**把 `moonshotai/kimi-k2.5` 直接替换成默认 `fast_model`
- 如果后续继续试：
  - 只能做很窄的离线 lab / 单 pack canary
  - 不适合直接切快报主链
