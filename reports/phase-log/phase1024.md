# phase1024

1. 这轮达到的目的
- 将 V12 被认可的组合模型链路沉淀成 Hotpost 可选 LLM route profile，而不是只回灌 prompt。

2. 当前状态变化
- `hotpost_quality.yaml` 新增 `llm_routing.profiles.hotpost_v12`：`semantic_model=deepseek/deepseek-v4-flash`，`writer_model=xiaomi/mimo-v2.5-pro`。
- `load_card_content_models()` 现在会读取 `route_profiles`，`card_content_llm_router` 提供显式 profile resolver。
- 默认 `fast_model / reasoning_model / hot lane override` 没变，`hotpost_v12` 不会自动切到全部生产流量。

3. 还没完成什么
- 还没有用同一批 V12 样本跑真实生产 prompt + `hotpost_v12` profile 的 live after 报告。

4. 下一步做什么
- 下一轮只在三 tab 实验、shadow run 或 backfill 验证里显式选择 `hotpost_v12`；确认输出接近 V12 报告后，再讨论是否设默认。
