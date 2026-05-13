# phase695

## 本轮完成
- 确认 hotpost 推理模型切换入口不是单一一处，而是两层：
  - 运行时配置：`HOTPOST_REASONING_MODEL`
  - 出卡生成层：`card_content_generator.load_card_content_models()`
- 修复了出卡生成层只读 `hotpost_quality.yaml`、不吃环境变量的问题，避免出现：
  - 搜索/服务层已经切模型
  - 出卡层还停在旧模型
- 本地 `backend/.env` 已明确切到：
  - `HOTPOST_REASONING_MODEL=z-ai/glm-5.1`

## 连通性验证
- 已用当前 `OPENROUTER_API_KEY` 对 `z-ai/glm-5.1` 做最小连通性测试。
- 结果：
  - 普通对话请求可连
  - `response_format=json_object` 也可连
  - 在主链同量级预算 `max_tokens=1400` 下，已实际返回：
    - `{\"ok\": true, \"msg\": \"connected\"}`
- 说明：
  - `z-ai/glm-5.1` 不是“接口可达但主链不可用”
  - 在当前 OpenRouter 兼容链下，可作为 hotpost 的 reasoning model 使用

## 代码改动
- `backend/app/services/hotpost/card_content_generator.py`
  - `load_card_content_models()` 现在优先读取：
    - `HOTPOST_FAST_MODEL`
    - `HOTPOST_REASONING_MODEL`
    - `HOTPOST_REASONING_ENABLED`
- `backend/.env`
  - 新增：
    - `HOTPOST_REASONING_MODEL=z-ai/glm-5.1`

## 验证
- `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_card_content_generator.py -q`
- 结果：`24 passed`
- 新增测试：
  - 环境变量覆盖 `reasoning_model` 生效
