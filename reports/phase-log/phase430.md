# Phase 430 - Full A 标杆合同差距审计

## 本轮目标

把 [`reports/t1价值的报告.md`](/Users/hujia/Desktop/RedditSignalScanner/reports/t1价值的报告.md) 正式当成 Full A 唯一内容结构标杆，审计当前代码和这个目标之间的差距，并判断产品方向是否已经跑偏。

## 结论先说

- 产品方向**没有变**
- 当前系统里 Full A 的 6 大结构骨架**还在**
- 但合同**没有真正落到后端硬门槛**
- 所以系统现在仍允许自己：
  - 只靠事实门槛拿到 `A_full`
  - 在 `B/C/X` 走另一套交付
  - 在前端靠 fallback 把结构“补出来”

这 3 件事就是当前最核心的漂移源。

## 审计范围

- 后端事实门禁：
  - `backend/app/services/facts_v2/quality.py`
- 后端结构化报告与报告装配：
  - `backend/app/services/analysis/analysis_rendering.py`
  - `backend/app/services/report/inline_structured_report_workflow.py`
  - `backend/app/services/report/report_assembly_workflow.py`
  - `backend/app/services/report/report_runtime_factory.py`
  - `backend/app/services/report/report_payload_builder.py`
- 前端报告交付：
  - `frontend/src/pages/ReportPage.tsx`
  - `frontend/src/lib/product-surface.ts`
  - `frontend/src/types/report/response.ts`
  - `frontend/src/types/report/schema.ts`

## 关键发现

### 1. `A_full` 现在还是“证据够硬”，不是“完整 Full A 报告”

`backend/app/services/facts_v2/quality.py` 的 `_determine_report_tier()` 当前只看：

- `good_pains`
- `good_brands`
- `solutions`

达到阈值就会返回 `A_full`。

这意味着现在的 `A_full` 只代表：

- 事实层通过了质量门禁

它**不代表**：

- 已经产出与 `t1价值的报告.md` 对齐的完整结构
- 已经拿到完整的 `decision_cards / market_health / battlefields / pain_points / drivers / opportunities`
- LLM 表达质量已经过关

### 2. `report_structured` 现在是可选增强，不是 Full A 硬门槛

`backend/app/services/analysis/analysis_rendering.py` 的 `render_structured_report_with_llm()` 当前行为：

- `C_scouting / X_blocked`：直接 `skipped`
- 缺 API key / facts / JSON 无效 / LLM 失败：返回 `failed/skipped`
- 不会反推 `report_tier`

`backend/app/services/report/inline_structured_report_workflow.py` 也是同样逻辑：

- 只要 `report_structured` 缺失，但当前条件不满足，就直接返回 `None`

结论：

- Full A 结构不是报告 tier 的判定前提
- 而是“有就用、没有也继续”

### 3. `B/C/X` 现在不是“同骨架简化版”

`backend/app/services/analysis/analysis_rendering.py` 的 `render_analysis_reports()` 当前逻辑：

- `X_blocked`：输出 `X_blocked` 说明 + scouting 报告
- `C_scouting`：直接走 `render_scouting_report()`
- 其他：走 `render_report()`

这说明当前系统是**分叉渲染**：

- `A/B` 一路
- `C/X` 另一路

而不是：

- 统一 Full A 骨架
- 再根据证据强弱把内容压缩成 B/C

这和本轮新合同冲突：

- `B/C` 必须是 Full A 基础上的简化版
- 不能完全脱离

### 4. 前端 fallback 掩盖了后端合同缺失

`frontend/src/pages/ReportPage.tsx` 里有 `buildFallbackStructuredReport()`。

当后端没给 `report_structured` 时，前端会临时拼一份：

- `decision_cards`
- `market_health`
- `battlefields`
- `pain_points`
- `drivers`
- `opportunities`

这虽然能保住页面不空，但副作用很明显：

- 页面看起来像是“系统已经交付了结构化报告”
- 实际却是前端在补洞
- 真正的后端合同缺口被隐藏了

### 5. 产品方向没丢，6 大结构骨架还在

前端类型和 schema 仍然明确保留了 Full A 的 6 大结构：

- `decision_cards`
- `market_health`
- `battlefields`
- `pain_points`
- `drivers`
- `opportunities`

说明这套产品方向没变，系统也没有改成完全别的东西。

问题只是：

- 没把这套结构升成“后端必须交付”的合同

## 当前和目标的真实差距

### P0 差距

1. `A_full` 缺少结构完整性门禁
2. `B/C` 没被约束为同骨架简化版
3. 前端 fallback 掩盖后端合同缺口

### P1 差距

1. `render_report()` 仍偏旧式 markdown 拼装，不是严格按 `t1价值的报告.md` 的表达力度生成
2. 结构化 LLM 成功与否没有进入正式验收主门禁
3. 测试里仍接受 `structured_llm_status = failed` 作为可保留合同

## 这轮的价值

这轮最重要的不是改了什么代码，而是把口径重新钉死了：

- 我们要的不是“事实够多就算 `A_full`”
- 我们要的是“系统交付出一份长得像 `t1价值的报告.md` 的完整报告”
- `B/C` 只是这个完整骨架的压缩版
- 不是另一套产品

## 下一步

进入下一轮时，应该先做 **Full A 系统合同固化**，顺序建议如下：

1. 定义 Full A / B / C 的统一结构合同
2. 把 `report_structured` 从“可选增强”升成 `A/B/C` 的正式交付骨架
3. 让 `A_full` 判定同时受“事实门槛 + 结构完整性门槛”约束
4. 删掉或降级前端 `fallback structured report`
5. 把验收测试改成围绕 `t1价值的报告.md` 结构做 contract check
