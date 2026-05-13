# Phase 551 - Trending 详情页细节收口与解读加深

## 时间
- 2026-03-28

## 发现了什么
1. 用户对 `trending` 详情页的核心不满已经收敛到两层：
   - 页面结构细节还不顺
   - 解读还偏表面，没把 LLM 的价值真正透出来
2. 前端当前问题主要有：
   - 顶部模式标签、关键词标题、数据说明层级还不够清楚
   - `代表帖子` 的正文和解释混在一起
   - `用户原话` 仍在用偏模板式说明
3. 后端当前问题主要有：
   - `trending` prompt 还没有强制产出“这条帖子/这句原话为什么值得看”的解释字段
   - 因此用户端只能做弱解释，容易显得浅

## 是否需要修复
- 需要。
- 这轮不再只修前端壳子，而是前后端一起收：
  - 页面层次
  - 解释字段
  - 人话文案

## 精确修复方法
### 1. 后端补强 trending 解读合同
- 更新：
  - `backend/app/schemas/hotpost.py`
  - `backend/app/services/hotpost/prompt_core.py`
  - `backend/app/services/hotpost/prompt_trending.py`
  - `backend/app/services/hotpost/report_llm.py`
- 改动：
  - `TopQuote` 新增 `why_important`
  - `prompt_trending` 现在要求：
    - `top_quotes[].why_important`
    - `post_annotations[].why_important`
  - `report_llm` 合并注解时同时写回 `why_relevant / why_important`

### 2. 前端重排顶部信息层
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.scss`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/content-helpers.ts`
- 改动：
  - `热点追踪` 模式标签上移居中
  - query 标题居中显示
  - 数据行补上观察窗口，形如：
    - `30 条信号 · generativeAI / aivideo · 近 30 天`
  - 整体视觉往下微调

### 3. 代表帖子与解读分层
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/sections.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/detail.scss`
- 改动：
  - `代表帖子` 的正文摘要和解释分开
  - 解释单独成块，标题固定为：
    - `简洁解读`

### 4. 用户原话不再只说模板话
- 更新：
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/sections.tsx`
  - `hotpost-mini/hotpost-mini-app/src/pages/velocity/content-helpers.ts`
- 改动：
  - 每条原话单独展示：
    - `这句话为什么值得看`
  - 优先吃后端返回的 `why_important`
  - 没有时才做很轻的本地解释

## 验证
- 后端定向：
  - `pytest backend/tests/services/hotpost/test_hotpost_prompts.py backend/tests/services/hotpost/test_hotpost_report_workflow.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
  - `18 passed`
- 小程序构建：
  - `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - `Compiled successfully`

## 这次执行的价值
- 把 `trending` 页面从“字段页”继续推进到“有解释力的分析页”。
- 这轮最重要的不是样式，而是：
  - 代表帖子为什么值得看
  - 用户原话为什么值得看
  - 这些解释不再只是前端猜，而是开始进入后端正式合同
