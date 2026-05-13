# phase696

## 本轮完成
- 确认当前前台 `快报/signal` 主链使用的是 `fast_model`，不是 `reasoning_model`。
- 按最新决策，将 `HOTPOST_REASONING_MODEL` 从 `z-ai/glm-5.1` 回切到 `xiaomi/mimo-v2-pro`。
- 保留出卡层“优先读取环境变量”的修复，避免后续再次出现：
  - 环境变量已改
  - 出卡层仍停在旧模型

## 当前有效配置
- `backend/.env`
  - `HOTPOST_REASONING_MODEL=xiaomi/mimo-v2-pro`
- `backend/config/hotpost_quality.yaml`
  - `reasoning_model: "xiaomi/mimo-v2-pro"`
- `load_card_content_models()` 实际返回：
  - `fast_model = x-ai/grok-4.1-fast`
  - `reasoning_model = xiaomi/mimo-v2-pro`
  - `reasoning_enabled = true`

## 说明
- 这次回切不是回退修复。
- 代码层“支持环境变量覆盖模型配置”的能力继续保留。
- 当前只是把 hotpost 的推理模型选择恢复到原设定。
