# phase1077

## 这轮达到的目的

按最新口径把 Hotpost `fast_model` 从 Pro 收缩为 `deepseek/deepseek-v4-flash`。

## 当前状态变化

`backend/config/hotpost_quality.yaml` 与 `backend/.env` 的 `HOTPOST_FAST_MODEL` 已同步改为 `deepseek/deepseek-v4-flash`。
V13 正式 profile 不变：语义理解仍是 `google/gemini-3-flash-preview`，写卡 / title repair / breakdown 仍是 `deepseek/deepseek-v4-pro`。
语义理解层已有独立 prompt，会先生成 `core_scene / supported_claim / risk_bounds` brief，再注入写卡 prompt。

## 还没完成什么

这轮只改模型配置和测试口径，没有重新发卡，也没有刷新小程序快照。

## 下一步做什么

补卡前确认运行时 `fast_model=deepseek/deepseek-v4-flash`，V13 profile 仍为 Gemini semantic + DeepSeek Pro writer。
