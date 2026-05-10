# Phase 590 - Rant 动作建议闭环落地

## Goal
- 不再只给 `rant` 结果一组追问关键词。
- 在不加新工程层的前提下，把现有 `pain_points / business_implication` 压成轻量、可执行的“先做什么”。
- 保持 `trending / opportunity` 不受影响。

## Work
- 后端：
  - `backend/app/schemas/hotpost.py`
    - `NextSteps` 增加 `recommended_actions`
  - `backend/app/services/hotpost/response_bundle.py`
    - 新增 `_build_rant_recommended_actions()`
    - 直接复用 `pain_points.business_implication / key_takeaway`
    - 兼容 `dict` 和模型对象两种运行时形态
  - `backend/app/services/hotpost/quality_contract.py`
    - 对 `recommended_actions` 做去空、去重、限长
  - `backend/app/services/hotpost/report_export.py`
    - markdown `下一步` 区块补动作建议
- 小程序：
  - `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts`
    - `HotpostNextSteps` 增加 `recommended_actions`
  - `hotpost-mini/hotpost-mini-app/src/pages/friction/helpers.ts`
    - 新增 `recommendedActions()`
  - `hotpost-mini/hotpost-mini-app/src/pages/friction/sections.tsx`
    - `06 / 下一步` 先显示“先做什么”，再显示追问关键词
- 测试：
  - `backend/tests/services/hotpost/test_hotpost_response_bundle.py`
    - 新增 dict / model 两类动作建议用例
  - `backend/tests/services/hotpost/test_hotpost_report_export.py`
    - 覆盖 markdown 导出动作建议
  - `backend/tests/services/hotpost/test_hotpost_report_llm.py`
    - 顺手把旧 prompt 断言对齐到当前合同

## Verification
- `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - `Compiled successfully`
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_response_bundle.py backend/tests/services/hotpost/test_hotpost_report_export.py -q`
  - `16 passed`
- `pytest backend/tests/services/hotpost/test_hotpost_report_llm.py::test_render_hotpost_prompt_contains_inputs -q`
  - `1 passed`
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost -q`
  - `167 passed`
- 真无缓存 live：
  - query=`为什么tiktok上做的内容有流量但却没有转化购买？`
  - `from_cache=false`
  - `status=completed`
  - `mode_state=standard`
  - `evidence_count=5`
  - `communities=["TikTokAds","TikTokshop"]`
  - `recommended_actions`：
    - `优先优化从广告点击到购买落地页的转化路径，或重新评估TikTok广告的定位策略，避免为无效互动付费。`
    - `先处理「转化归因困难」：需要建立或整合能够捕获所有转化路径（包括非网站渠道）的归因系统，否则无法准确衡量广告ROI。`

## Result
- `rant` 不再只有“问题是真的”和“继续追哪些词”。
- 现在已经能补上第一层闭环：
  - 先改哪一刀
  - 为什么先改这一刀
- 这层闭环完全复用现有分析结果，没有新增 worker、状态机或额外 LLM 职责。

## Next
- 进入小程序真页面验收：
  - 看 `06 / 下一步` 是否终于像“先做什么”
  - 看动作建议有没有继续说正确的废话
  - 如果还有 AI 味，再只收文案力度，不回头长工程层
