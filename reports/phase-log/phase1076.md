# phase1076

## 这轮达到的目的

按用户要求把 Hotpost V13 正式出卡 LLM 路由改成 `google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro`。

## 当前状态变化

`hotpost_v13_title_standalone` 已改为 Gemini 做语义理解、DeepSeek v4 Pro 做中文写卡和 title-only repair。
`fast_model / reasoning_model` 以及 `backend/.env` 里的 Hotpost 默认模型已从 `xiaomi/mimo-v2-pro` 改为 `deepseek/deepseek-v4-pro`。
活跃 eval / shadow 测试中的当前模型样例也已同步；历史 reports / checkpoints 保持原样，作为当时运行记录。
V13 breakdown 与 `refresh_breakdown_content()` 继续跟随 production profile writer，也就是 `deepseek/deepseek-v4-pro`。

## 还没完成什么

这轮只改 LLM 配置和测试，没有重新发卡，也没有刷新小程序快照。

## 下一步做什么

补卡前先确认运行时 profile 仍解析为 `google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro`，再进入 collect / review / publish。
