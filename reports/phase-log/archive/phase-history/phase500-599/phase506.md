# Phase 506 - 报告输出质量层第一段落地（合同冻结 + brief + review）

## 时间
- 2026-03-27

## 目标
- 在不改变现有 Full A 报告外部结构的前提下，给报告主链接入第一段内部质量层：
  - 冻结外部结构合同
  - 增加卡片/长报告一致性合同
  - 增加证据链接可点击合同
  - 给 narrative 主链增加 `brief -> review` 的最小版本

## 执行内容

### 1) 前端合同冻结
- 新增：
  - `frontend/src/lib/report-contract.ts`
- 新增能力：
  - 固定检查 markdown 是否仍为 `1-7` 章节
  - 检查 markdown 是否仍覆盖 canonical 的战场/痛点/驱动力/机会标题
  - 检查 canonical evidence 是否都能转成可点击的 Reddit 链接
- 关键口径：
  - 合同只检查“结构与证据”，不允许前端擅自扩结构
  - 相对路径可自动补齐，但非 Reddit 外链不算合格证据

### 2) 前端契约测试补齐
- 更新：
  - `frontend/src/tests/contract/report-schema.contract.test.ts`
  - `frontend/src/tests/contract/report-api.contract.test.ts`
- 结果：
  - 新增“一致性 + 可点击证据”断言
  - 前端合同 + 集成回归：
    - `3 files passed / 10 tests passed`

### 3) 后端 brief 层最小落地
- 新增：
  - `backend/app/services/report/report_brief_builder.py`
- 作用：
  - 把 `canonical_report_json + facts_slice` 压成更短的 `report_brief`
  - 保留固定章节、标题、证据链和关键 facts focus
  - 不再把 narrative prompt 直接喂整份冗长原始事实包

### 4) narrative review 合同接入
- 新增：
  - `backend/app/services/report/report_markdown_contract.py`
- 更新：
  - `backend/app/services/report/narrative_report_workflow.py`
- 新能力：
  - narrative markdown 生成后，不只查固定标题和禁语
  - 还要对照 canonical 检查：
    - 章节是否齐
    - section 4/5/6/7 是否仍覆盖 canonical 标题锚点
  - 漂移则拒绝进入正式交付

### 5) 离线门禁升级
- 更新：
  - `makefiles/test.mk`
- `acceptance-offline-gate` 已纳入：
  - `test_report_brief_builder.py`
  - `test_report_markdown_contract.py`
  - `test_narrative_report_workflow.py`

## 验证结果

### 前端
- `cd frontend && npm test -- --run src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts src/pages/__tests__/ReportFlow.integration.test.tsx`
- 结果：
  - `3 files passed`
  - `10 tests passed`

### 后端
- `cd backend && SKIP_DB_RESET=1 pytest tests/services/report/test_report_brief_builder.py tests/services/report/test_report_markdown_contract.py tests/services/report/test_narrative_report_workflow.py -q`
- 结果：
  - `7 passed`

### 离线总门禁
- `make acceptance-offline-gate`
- 结果：
  - `72 passed`

### Live 验收
- `make acceptance-live-final`
  - 输出：`backend/reports/local-acceptance/open_question_live_final_1774585179.json`
  - 结果：`1/1 accepted`，`A_full`
- `make acceptance-live-smoke`
  - 输出：`backend/reports/local-acceptance/open_question_live_smoke_1774585612.json`
  - 结果：`1/3 accepted`
  - 失败点：
    - `Tools_EDC -> C_scouting (scouting_brief)`
    - `Family_Parenting -> B_trimmed`

## 四问回顾
1. 发现了什么？
- 新增的输出质量层没有破坏主链结构，也没有引入新的 narrative 合同失败。
- `final` 能继续稳定 `A_full`，说明新链路本身可用。
- `smoke` 的失败仍然是旧问题：live 数据样本波动导致的 tier 降级，不是这轮的 `brief/review` 把报告写坏。

2. 是否需要修复？
- 需要，但下一刀应继续打 live 低样本/噪音，不是回头撤掉这轮质量层。

3. 精确修复方法？
- 已完成的这轮修复：
  - 把“外部结构不变”写成硬合同
  - 把“证据链接必须可点击”写成硬合同
  - 把 narrative 的输入改成 brief
  - 把 narrative 的输出加上 canonical review

4. 下一步系统性计划是什么？
- 第二段继续推进：
  - 做更明确的 review/repair 策略，而不是只 reject
  - 针对 `Tools_EDC / Family_Parenting` 做 live 噪音和低样本收口
  - 等 smoke 恢复稳定后，再继续 prompt 减肥

5. 这次执行的价值是什么？达到了什么目的？
- 报告主链第一次有了真正可执行的“内部质量层”，而且不改外部结构。
- 现在我们终于不是只靠长 prompt 撑质量，而是开始靠合同、brief 和 review 控制输出。
