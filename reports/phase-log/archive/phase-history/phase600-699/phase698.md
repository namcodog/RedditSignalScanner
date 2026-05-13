# phase698

## 本轮完成
- 对当前 `fast_model` 与 `moonshotai/kimi-k2.5` 做了真实 A/B 评估
- 范围：
  - `signal / validate`
  - 同一批真实候选
  - 不写回生产

## 可用性
- `moonshotai/kimi-k2.5` 在 OpenRouter 上模型名存在
- 最小 `json_object` 请求可连

## A/B 结果
- `upstream-winds`
  - Kimi 语义更完整，但明显更慢
- `agent-builder`
  - 成熟 pack 上输出基本与当前模型一致
  - 但延迟更高
- `selection-signals`
  - Kimi 真实返回 `invalid JSON`
- `paid-economics`
  - Kimi 真实返回 `invalid JSON`

## 结论
- 当前不建议把 `moonshotai/kimi-k2.5` 直接切成默认 `fast_model`
- 原因：
  - 结构化输出稳定性不够
  - 延迟偏高
  - 在成熟 pack 上没有稳定带来更好的前台效果
