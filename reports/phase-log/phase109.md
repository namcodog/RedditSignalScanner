# Phase 109 - 前端修复验收（API 对齐）

日期：2026-01-19

## 验收范围
- API 修复：metrics、report PDF、sources 账本、decision-units
- 新增页面与路由：DecisionUnitsPage、Admin 入口
- 类型与请求入参补全

## 已通过项
1) **metrics 路径修复**  
   - 位置：`frontend/src/api/metrics.ts`  
   - 结果：已改为 `'/metrics/daily'`，避免双 `/api`。

2) **PDF 导出鉴权与 baseURL**  
   - 位置：`frontend/src/pages/ReportPage.tsx`  
   - 结果：使用 `auth_token` + `VITE_API_BASE_URL`。

3) **sources 账本接入与 UI 展示**  
   - 位置：`frontend/src/api/analyze.api.ts`、`frontend/src/pages/ReportPage.tsx`  
   - 结果：新增 `getTaskSources` 并在报告页显示质量 Banner。

## 验收未通过项（需要修复）
1) **TaskSourcesResponse 未导出导致类型编译失败**  
   - 位置：`frontend/src/types/index.ts`  
   - 现状：`TaskSourcesResponse` 未从 `task.types.ts` 导出。  
   - 影响：`frontend/src/api/analyze.api.ts`、`frontend/src/pages/ReportPage.tsx` 的 `@/types` 引用会报错。

2) **DecisionUnit 接口返回字段不匹配**  
   - 前端：`frontend/src/api/decision-units.api.ts` / `frontend/src/pages/DecisionUnitsPage.tsx`  
   - 后端：`backend/app/api/v1/endpoints/decision_units.py`  
   - 现状：后端返回字段为 `id/title/summary/confidence/...`，前端用的是 `decision_unit_id/primary_concept/explanation/score`。  
   - 影响：列表渲染与反馈提交会失效（`unit.decision_unit_id` 为空）。

3) **useToast 使用方式错误**  
   - 位置：`frontend/src/pages/DecisionUnitsPage.tsx`  
   - 现状：`const { toast } = useToast();`，但 `useToast()` 返回的是 `{ success, error, ... }`。  
   - 影响：`toast.success` 为 undefined，反馈提示会报错。

## 结论
本轮修复已解决 metrics 与 PDF 导出的核心问题；sources 账本接入已落地。  
DecisionUnit 模块存在字段契约不匹配与 toast 使用错误，需修复后再做二次验收。
