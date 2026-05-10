# Phase 442 - 标准样板回流口径改空白输入 + Full A 长报告对齐第一刀

## 发现了什么

### 1. 标准样板回首页的默认行为还不对

- 用户已经明确拍板：
  - 标准样板只负责展示
  - 回首页后输入框应该保持空白
  - 不要默认把标准题塞回输入框
- 上一版虽然把“标准样板 -> 输入页”接上了，但本质仍然是在替用户延续标准题。
- 这会把主链搞脏：
  - 用户明明要开始自己的真实问题
  - 系统却还在替他保留原题和黄金路径

### 2. Full A 长报告目前更像“能生成”，还不是“对齐标准文档”

- 当前 narrative 主链已经打通，但 prompt 仍偏宽松。
- 它更像是在让模型“写一份完整报告”，而不是明确对齐 [`reports/t1价值的报告.md`](/Users/hujia/Desktop/RedditSignalScanner/reports/t1价值的报告.md)。
- 所以现有长报告里仍可能出现几类偏机器味的句子：
  - `这是系统生成的统一结构报告`
  - `覆盖 X 帖 / Y 评论，趋势可用于继续决策`
  - `先验证问题复现频率，再决定是否深挖`

## 是否需要修复

- 需要，而且这两件事是同一轮里最该先收的两个点：
  1. 主链默认入口必须更干净
  2. Full A 长报告必须开始往统一标准文档收口

## 精确修复方法

### 1. 标准样板返回首页改成默认空白

- `frontend/src/lib/standard-report.ts`
  - `buildStandardPrefillState()` 不再带回 `prefillProductDescription`
  - 不再带回 `topic_profile_id`
  - 改成只带：
    - `prefillSource=standard-case`
    - `prefillStandardTitle`
    - `prefillPromptSuggestion`
    - 一条轻提示文案

- `frontend/src/pages/InputPage.tsx`
  - 标准样板回流时：
    - 输入框保持空白
    - 显示轻提示：`刚看过这份标准样板`
    - 显示：`刚看的是：<标题>`
    - 显示一条参考式问题描述
  - 不再保留黄金路径，不再默认代用户续跑标准题

- `frontend/src/pages/StandardCasePage.tsx`
  - CTA 改成：`回首页写我的问题`
  - 文案明确说明：首页输入框会是空白的，标准题只做参考

- `frontend/src/pages/StandardReportPage.tsx`
  - 底部 CTA 改成：`回首页写我的问题`
  - 同步把说明文案改成“标准样板只留方向，不替你填题”

### 2. Full A narrative prompt 对齐标准文档第一刀

- `backend/app/services/llm/report_prompts.py`
  - `REPORT_SYSTEM_PROMPT_V9` 收紧成：
    - 先说结论，再说依据，再说动作
    - 不再允许“执行痕迹句”
    - 不允许把 `（数据不足）` 当口头禅
  - `build_complete_report_v9()` 明确写死：
    - 对齐 `reports/t1价值的报告.md`
    - 章节结构改成更接近标准文档：
      - `已分析赛道（Analyzed Niche）`
      - `决策风向标`
      - `概览（市场健康度诊断）`
      - `核心战场推荐（T1 社区视角）`
      - `用户痛点（User Pain Points）`
      - `Top 购买 / 决策驱动力（Drivers）`
      - `商业机会（Opportunities）`
    - 每一块都明确要求：
      - 结论
      - 依据
      - 对下一步有什么用
  - 额外补了禁句清单，直接禁止当前最常见的机器味产物

## 验证

### 前端

- `cd frontend && npm test -- src/pages/__tests__/InputPage.test.tsx src/pages/__tests__/StandardReportPage.test.tsx src/pages/__tests__/StandardCasePage.test.tsx`
  - `11 passed`
- `cd frontend && npm run build`
  - 通过

### 后端 prompt

- `SKIP_DB_RESET=1 pytest backend/tests/services/llm/test_report_prompts_v9.py -q`
  - `6 passed`

> 说明：
> 默认 `pytest` 会触发全局 DB reset fixture，在 sandbox 里访问本地 `5432` 被拦。
> 这轮是纯 prompt 测试，所以按仓库安全开关加了 `SKIP_DB_RESET=1` 重跑。

## 这次执行的价值

- 首页默认主链被重新拉干净了：
  - 标准样板负责展示
  - 开放输入负责真实问题
- Full A 长报告也开始从“能生成”升级到“按统一标准文档生成”

## 下一步系统性计划

1. 跑一轮真实 narrative 样本抽检
   - 至少抽 1-2 个标准题
   - 对照 `t1价值的报告.md` 看章节力度、依据密度、机器味残留

2. 如果文本仍偏弱
   - 再补第二刀 prompt，不动主链结构
   - 优先补“用户痛点”和“商业机会”两块

3. 等 narrative 抽检过关后
   - 再决定是否重导出 6 份标准样板快照
