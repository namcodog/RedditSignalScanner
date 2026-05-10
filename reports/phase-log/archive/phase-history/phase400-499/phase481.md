# Phase 481: canonical 社区出口打通与三领域 live 复验

## 本轮目标

- 修 `insights.top_communities -> canonical_report_json.target_communities` 这条装配断点。
- 不扩散到前端视觉层，只补统一社区出口。
- 用 3 条真实 live 复验：
  - 电商
  - EDC
  - AI workflow

## 本轮执行

### 1. 补 canonical 顶层社区出口

- 修改：
  - `backend/app/services/report/structured_report_fallback.py`
- 动作：
  - `build_structured_report_fallback(...)` 现在会显式输出：
    - `target_communities`
  - 优先吃：
    - `insights.top_communities`
  - 如果没有，再回退到：
    - `sources.communities_detail / communities`
  - `enforce_structured_report_contract(...)` 也同步补了：
    - `_normalize_top_communities()`
  - 保证 candidate / fallback / battlefields 至少有一条统一社区出口

### 2. 同步前端类型合同

- 修改：
  - `frontend/src/types/report/response.ts`
  - `frontend/src/types/report/schema.ts`
- 动作：
  - `StructuredReport` 新增可选字段：
    - `target_communities?: string[]`

### 3. 补回归测试

- 修改：
  - `backend/tests/services/report/test_structured_report_fallback.py`
- 新增验证：
  - fallback 顶层会输出 `target_communities`
  - contract enforce 后仍保留顶层 `target_communities`

### 4. 定向回归

- 通过：
  - `pytest backend/tests/services/report/test_structured_report_fallback.py backend/tests/services/report/test_analysis_payload_loader.py backend/tests/schemas/test_schemas.py -q`
  - `40 passed`
- 通过：
  - `cd frontend && npm test -- --run src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/StandardReportPage.test.tsx`
  - `11 passed`

### 5. 三领域真实 live 复验

- 隔离 runtime：
  - backend `24351`
  - analysis-live `24352`
  - bulk-live `24353`

#### 电商

- `task_id = 731120bf-dd01-424c-8cec-29e991c7e7d6`
- `A_full`
- `canonical_report_json.target_communities`：
  - `r/dropshipping`
  - `r/shopify`
  - `r/ecommerce`
  - `r/SaaS`

#### EDC

- `task_id = 23100670-c1e8-4244-893b-4f38ca8b0f8e`
- `B_trimmed`
- `canonical_report_json.target_communities`：
  - `r/EDC`
  - `r/Tools`
  - `r/flashlight`
  - `r/knifeclub`

#### AI workflow

- `task_id = 2b138a4f-c8af-43e8-90dd-e7f735a9a349`
- `B_trimmed`
- `canonical_report_json.target_communities`：
  - `r/ChatGPT`
  - `r/LocalLLaMA`
  - `r/ClaudeAI`
  - `r/Notion`

## 关键结论

- `target_communities` 这条 canonical 断点已经被打通。
- 现在社区信息不再停在 `insights.top_communities`，已经能进入最终 report payload。
- 三领域 live 都已经能看到顶层 `canonical_report_json.target_communities`。

## 当前剩余问题

现在更深的瓶颈已经继续收敛：

1. 社区出口不再是主因
   - 这条线已经接通。

2. 多领域洞察转译仍然偏半成品
   - 例如：
     - `高频抱怨：英文原句...`

3. 弱领域仍然卡样本深度 / query focus
   - 尤其：
     - `Home_Lifestyle`
     - `Family_Parenting`

## 下一步

1. 继续提升 pain/opportunity 的通用中文转译质量
2. 优先打 `Home_Lifestyle / Family_Parenting` 的 query focus 和样本深度
3. 再跑一轮 8 领域横向 live，看：
   - `A_full` 数量是否上升
   - `关键痛点 2/3` 是否继续减少
   - 社区信息是否继续稳定保留
