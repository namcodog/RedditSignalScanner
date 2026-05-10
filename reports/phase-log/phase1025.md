# phase1025

1. 这轮达到的目的
- 用非 V12 旧样本跑出 `hotpost_v12` shadow 审核包，交给人工验收。

2. 当前状态变化
- 新增只读脚本 `backend/scripts/evals/run_hotpost_v12_shadow_new_samples.py`，输出 `reports/evals/hotpost_v12_shadow_new_samples_review_packet.md` 和 JSON。
- 本轮跑了 `6` 条新样本：`signal 2 / hot 2 / breakdown 2`，与 V12 旧样本无重叠，全部生成成功。
- 确认 shell 里有旧 OpenRouter key；按项目 loader 读取 `backend/.env` 后，`deepseek/deepseek-v4-flash` 和 `xiaomi/mimo-v2.5-pro` 可正常调用。

3. 还没完成什么
- `4/6` 条仍有轻微长度残留，主要是字段超出 V12 建议字数；没有命中标题党词、行动建议禁词或死物主语禁词。

4. 下一步做什么
- 由人工审核报告质量；如果认可，下一步再决定是否把 `hotpost_v12` 用于更大 shadow 批次或局部 backfill。
