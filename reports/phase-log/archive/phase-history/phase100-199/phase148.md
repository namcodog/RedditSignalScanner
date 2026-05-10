# Phase 148 - API 联调口径对齐（/api vs /api/v1 + Admin 返回格式）

日期：2026-01-22

## 目标
- 对齐 API 文档与后端实际路由范围（/api vs /api/v1）。
- 明确 Admin 返回格式的包裹型/直返型边界，避免前后端联调踩坑。

## 变更
- `docs/API-REFERENCE.md`：
  - 修正 `/api/v1` 仅覆盖 v1 模块的口径。
  - 明确 Admin 直返接口清单（tasks/ledger、metrics、facts）。
  - 诊断接口鉴权改为 Admin JWT。
  - 补充 LLM 未配置时的调试回退说明。
- `docs/PRD/PRD-02-API设计.md`：
  - 同步 `/api/v1` 范围口径。
  - 细化 Admin 返回格式（包裹型/直返型）。
  - 补充 LLM 调试回退说明。
- `docs/PRD/PRD-07-Admin后台.md`：
  - 修正 PRD-10 引用路径大小写。
  - 补充 Admin 返回格式提示。

## 测试
- 未运行（仅文档对齐）。

## 结果
- API/PRD 口径与当前路由实际一致，前后端联调风险下降。
