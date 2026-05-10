# phase1078

## 这轮达到的目的

完成 Hotpost V13 semantic prompt 优化，并审计 LLM 配置是否真实生效。

## 当前状态变化

V13 semantic brief 从 3 字段扩为主体、场景、证据 basis、张力、why_now、边界、写作焦点和禁写结论。
V13 breakdown prompt 现在也会收到同一份 semantic brief，不再只依赖已写出的 signal draft。
运行时确认：`fast_model=deepseek/deepseek-v4-flash`，`reasoning_model=deepseek/deepseek-v4-pro`，V13 profile 为 `google/gemini-3-flash-preview -> deepseek/deepseek-v4-pro`。

## 还没完成什么

这轮没有重新发卡、没有刷新小程序快照，也没有改旧 eval v8-v12 的历史实验模型口径。

## 下一步做什么

下一轮真实补卡前，抽样看 Gemini semantic brief 是否过长或过短；如不稳，再把 semantic prompt 拆成独立模板文件。
