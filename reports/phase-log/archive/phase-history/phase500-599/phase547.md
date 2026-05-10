# Phase 547 - Mini Hotpost Trending 详情页第二轮收口

## 1. 发现了什么？

- `trending` 详情页已经接上真实后端，但用户继续验收时暴露出 4 个成组问题：
  - 热门词结果里仍有英文解读，阅读割裂。
  - `trending` 默认时间窗过宽，容易把一年前的帖子带进代表帖。
  - 热门大词即便证据足够，也不会切到重模型。
  - 前端“代表帖子 / 用户原话 / 下一步”三块的价值表达还不够清楚。
- 额外确认到一个运行态事实：
  - 旧 `claude` 查询命中了缓存，所以页面仍会看到老的 `time_filter=all` 和英文结果。
  - 这不是本轮新代码没生效，而是历史缓存结果没刷新。

## 2. 是否需要修复？

- 需要，而且必须一次成组修，不能继续零散补丁。

## 3. 精确修复方法

### 后端

- `backend/config/hotpost_quality.yaml`
  - 新增 `query_resolution.default_time_filters`
  - 把 `trending` 默认时间窗改为 `month`
  - `llm_routing.reasoning_trigger_modes` 增加 `trending`
  - 新增 `reasoning_min_evidence_by_mode.trending=20`
- `backend/app/services/hotpost/hotpost_config.py`
  - runtime config 接入 `default_time_filters`
  - runtime config 接入 `reasoning_min_evidence_by_mode`
- `backend/app/services/hotpost/hotpost_runtime.py`
  - `resolve_hotpost_time_filter` 支持配置驱动默认值
- `backend/app/services/hotpost/service.py`
  - 用 runtime config 驱动 time filter
  - 把 `reasoning_min_evidence_by_mode` 透传到 workflow
- `backend/app/services/hotpost/search_workflow.py`
  - `trending` 在证据足够时允许走重模型
  - tie 情况下 `trending` 也允许保留 reasoning 结果
- `backend/app/services/hotpost/prompt_core.py`
  - 强化合同：所有面向用户的解释字段必须输出简体中文
- `backend/app/services/hotpost/response_bundle.py`
  - `trending` 的 `next_steps.suggested_keywords` 改为优先吃 `trending_keywords`
  - 不再默认退回输入 query 自己

### 小程序

- `hotpost-mini/hotpost-mini-app/src/pages/velocity/content-helpers.ts`
  - 新增：
    - `followupQueries`
    - `representativePostLimit`
    - `quoteValueNote`
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/sections.tsx`
  - `代表帖子` 改为按信号强度动态展示 3/4/5 条
  - `用户原话` 每条都补一句“为什么值得看”
  - `下一步` 改成“推荐下一步追问”
  - 关键词点击后直接进入下一轮热点追踪
- `hotpost-mini/hotpost-mini-app/src/pages/velocity/index.tsx`
  - `PostSection` 改为吃完整 `HotpostResult`，不再固定只取 3 条

## 4. 下一步系统性的计划是什么？

- 让你重新跑一次新的热门词查询，确认：
  - 页面是否已经进入中文解释
  - `观察窗口` 是否稳定是 `近 30 天`
  - 热门词是否能切到重模型
- 如果这轮体验认可，再继续把同一套口径复制到 `rant / opportunity`。

## 5. 这次执行的价值是什么？

- 把 `trending` 详情页从“真数据但还不够像产品”，推进到“后端判断更准，前端表达更像用户真正会用的分析页”。
- 当前进度判断：
  - 热点追踪真实链路：`100%`
  - 热点追踪详情页价值表达：`约 96%`

## 验证

- 后端定向：
  - `pytest backend/tests/services/hotpost/test_hotpost_time_filter.py backend/tests/services/hotpost/test_hotpost_runtime_config.py backend/tests/services/hotpost/test_hotpost_prompts.py backend/tests/services/hotpost/test_hotpost_response_bundle.py backend/tests/services/hotpost/test_hotpost_search_workflow.py backend/tests/services/hotpost/test_hotpost_search_service.py -q`
  - `27 passed`
- 小程序构建：
  - `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - `Compiled successfully`
