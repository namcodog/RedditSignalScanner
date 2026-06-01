# phase1149 - Hotpost V13 模型链路稳定性修复落地

## 这轮达到的目的
- 针对 2026-06-01 出卡里暴露的模型空 JSON、坏 JSON、阶段超时和 trace 不透明问题，补上工程级修复。

## 当前状态变化
- OpenAI-compatible SDK 请求现在显式带 `timeout`，不再只依赖外层等待。
- `_generate_json()` 已增加阶段级 `asyncio.wait_for`，`semantic_brief / writer / draft_precheck / json_retry / json_repair` 会记录子阶段 trace。
- 空响应被分类为 `empty_response`，不会再走同模型修复；前后夹文字但中间有 JSON object 的响应会先抽取 JSON。
- `draft_precheck` 阶段超时会落成 `REWRITE + precheck_error + stage_timeout`，不把整条 seed 链路直接打死。

## 还没完成什么
- 这轮没有切换模型渠道，也没有自动 fallback；DeepSeek / Gemini 渠道健康仍要在下一轮真实出卡里观察。

## 下一步做什么
- 下一轮按运营计划 seed / review 时，重点看 generation trace 的 `sub_stages`、`error_type` 和 precheck 分布，确认超时是否回到正常等待范围。
- 验证通过后，再考虑是否继续优化 AI 预检规则本身。
