# Phase 450 - Full A 漂移校准与 PayPal 黄金样板重对齐

## 发现了什么？

- 用户这轮指出的核心问题是成立的：
  - 所谓 `Full A` 报告里仍有明显机器腔
  - 前端证据链链接应该能直接跳 Reddit，但现场感知不稳定
  - 首页标准卡、标准报告页和真实 live 结果之间已经出现漂移
- 这次把问题重新拆开后，根因不是前端单点，而是三层一起偏了：
  1. `narrative markdown` 仍允许“趋势可用于继续决策 / 立即投放 / 测试广告 / 痛点销售比”这类机器句进 live
  2. `canonical_report_json` 的合同清洗不够严，候选 structured 文案里这些词会直接透传到卡片页
  3. `frontend/public/topic-profile-reports/` 里的标准快照还挂着旧任务，导致首页标准卡和当前 live 结果不是同一版

## 是否需要修复？

- 需要，而且这轮已经先把 PayPal 这条黄金样板收回新口径。
- 但要实话实说：
  - 现在不能说“Full A 已经 100 分”
  - 这轮做到的是“把明显失控的漂移拉回来，并把 PayPal 标准样板切到当前更干净的 live 结果”
  - 当前剩余缺口仍有：
    - PayPal 第 2 张机会卡还偏泛
    - 其余 5 张标准快照还没按这轮新口径统一刷新

## 精确修复方法

### 1. 给“机器腔”加硬门禁

- 更新：
  - `backend/app/services/report/content_guardrails.py`
  - `backend/app/services/report/narrative_report_workflow.py`
  - `backend/app/services/llm/report_prompts.py`
- 新增/收紧：
  - 把 `趋势可用于继续决策 / 结论已形成可读结构 / 痛点销售比 / 立即投放 / 测试广告` 认定为坏文案
  - narrative markdown 命中这些词时直接拒收，不让坏长报告进入 live
  - prompt 明确禁止这类运营/系统口头禅，要求动作建议写成“先去哪看、拿什么案例切入、先验证哪类人”

### 2. 收紧 canonical structured 合同

- 更新：
  - `backend/app/services/report/structured_report_fallback.py`
- 修复点：
  - structured 合同里的单字段与列表字段都开始拒收机器腔
  - `health_assessment` 不再允许任意漂移，必须回到 `进场信号：...`
  - Reddit 社区标签大小写去重，避免 `r/ecommerce / r/Ecommerce` 重复出现
  - fallback 里的 `linked_pain_cluster` 不再被英文脏字段顶掉，优先回落到中文具体痛点

### 3. 重跑 PayPal live，并刷新标准快照

- 真实 live 任务：
  - 第一轮重跑：`f2c77076-487c-4045-a473-b7e7903b7c3f`
  - 第二轮重跑：`d5fac4b8-e913-4251-8e90-900ffd6a19ce`
  - 当前选用标准样板：`c8cd97d1-5a1f-49a5-a2ce-7c1e137ddc07`
- 当前选用样板的真实状态：
  - `report_tier=A_full`
  - `metadata.llm_used=true`
  - 首页 guidance 与标准快照题面都已切成：
    - `帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。`
- 已更新：
  - `frontend/public/topic-profile-reports/cross-border-paypal.json`
  - `frontend/public/topic-profile-reports/index.json`

## 验证

- backend 定向测试：
  - `cd backend && ../.venv/bin/pytest tests/services/report/test_content_guardrails.py tests/services/report/test_structured_report_fallback.py tests/services/llm/test_report_prompts_v9.py -q`
  - `17 passed`
- fallback 补测：
  - `cd backend && ../.venv/bin/pytest tests/services/report/test_structured_report_fallback.py -q`
  - `7 passed`
- frontend 定向测试：
  - `cd frontend && npm test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/StandardReportPage.test.tsx src/pages/__tests__/ReportPage.test.tsx`
  - `17 passed`
- py_compile：
  - `content_guardrails.py`
  - `structured_report_fallback.py`
  - `narrative_report_workflow.py`
  - `report_prompts.py`
  - `guidance.py`
  - 全部通过
- 真实 live：
  - `run_live_report_acceptance.py --topic-profile-id cross_border_payment_v1`
  - 当前标准样板任务 `c8cd97d1-5a1f-49a5-a2ce-7c1e137ddc07`
  - `/api/report` 抽检确认：
    - `A_full`
    - `llm_used=true`
    - evidence URL 为绝对 Reddit 链接

## 下一步系统性的计划是什么？

1. 不要急着说“Full A 已经收完”。
2. 先继续只盯 PayPal，把第 2 张机会卡从“泛化 fallback”继续收成具体产品机会。
3. 然后把其余 5 张标准快照按同一新口径刷新，否则首页 6 卡仍会一半新、一半旧。
4. 最后再回到前端人工验收，因为那时你看到的才是当前真正的交付真相源。

## 这次执行的价值是什么？

- 这轮不是“修了一点前端文案”，而是把 `Full A` 漂移问题重新打回了生成链本身。
- 更重要的是，PayPal 这条黄金样板现在已经从旧快照和旧 prompt 中脱身，重新对齐到真实 live 输出。
- 也就是说，后面你再盯这条样板时，看到的是当前系统的真实状态，而不是历史残影。
