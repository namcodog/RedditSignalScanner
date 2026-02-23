# Phase 200

## 目标
- 前端适配后端结构化字段与 SSE 队列事件。

## 变更
- 更新 Hotpost 类型：`frontend/src/types/hotpost.ts`
  - 补齐痛点/机会/工具/用户画像/市场机会结构
  - status 扩展（waiting/completed）
- Hotpost 结果页对齐后端字段：`frontend/src/pages/hotpost/HotPostResultPage.tsx`
  - 兼容 `unmet_needs`/`opportunities`
  - 兼容 `market_opportunity` 对象
  - 兼容 workarounds 对象结构
  - 迁移意向进度条与痛点字段兜底
- SSE 事件类型扩展：`frontend/src/types/sse.types.ts`
  - 新增 `queue_update`/`ping`，task_id 改为可选并支持 query_id

## 验证
- 未运行前端构建/测试（需联调时由前端或 CI 验证）。

## 结论
- 前端字段与后端输出结构保持一致，可消费三套 Prompt 输出与 SSE 队列状态。

## 影响范围
- 仅爆帖速递前端页面与类型。
