# Phase 566 - Rant 重构第一轮落地

## 1. 发现了什么？

- `rant` 当前最需要先收的是三层，不是继续改 prompt 细节：
  - query contract
  - retrieval gate
  - representative evidence projection
- 旧测试里还绑定着旧契约：
  - 默认认为 `expanded_terms` 必须保留某个短语
  - 默认允许 `why_important` 用兜底话术补齐
- 小程序页里的两个最伤信任点也已明确：
  - `代表帖子` 会直接拿 `top_posts`
  - `流失与替代` 会直接展示 `competitor_mentions`

## 2. 是否需要修复？

需要，而且这轮已经按“去兜底、去假分析、低耦合”收了一轮。

## 3. 精确修复方法？

### 后端

- `backend/app/services/hotpost/query_planner.py`
  - `rant` 的 `core_terms` 改为优先从 `search_query` 提取核心锚点，不再直接把扩展搜索短语当核心词。
- `backend/app/services/hotpost/evidence_collection_workflow.py`
  - `rant` 正式启用 `precision.keep` 门禁。
  - 没形成真实判断时，不再生成：
    - `评论活跃`
    - `最近讨论升温`
    - `信号密度更高`
    这类 `why_important` 兜底话术。
- `backend/app/services/hotpost/detail_builder.py`
  - `top_rants / top_discovery_posts` 不再把 `why_relevant` 冒充成 `why_important`。

### 小程序

- `hotpost-mini/hotpost-mini-app/src/pages/friction/helpers.ts`
  - `代表帖子` 改为优先展示 `pain_points[].evidence_posts`
  - `postInterpretation / quoteInterpretation` 改成：
    - 只有后端真给了 `why_important` 才展示
    - 否则不再自己编解释
  - 增加 `stableMigrationDestinations()`
- `hotpost-mini/hotpost-mini-app/src/pages/friction/sections.tsx`
  - `流失与替代` 改为只认 `migration_intent.destinations`
  - 没稳定目的地时整块不显示
  - `代表帖子 / 用户原话` 的解释区块改为无内容就不渲染
- `hotpost-mini/hotpost-mini-app/src/services/hotpost.ts`
  - 补齐 `migration_intent.destinations` 类型

## 4. 下一步系统性的计划是什么？

1. 接着收第二刀：
   - migration contract
   - preview contract
2. 再跑带 worker 的真实 `rant` query
3. 最后收页面人话表达和 `next_steps`

## 5. 这次执行的价值是什么？

这轮把 `rant` 从“继续会说废话的页面”推进到了“没有真实判断就少说”的状态。

最关键的价值不是多了什么，而是少了什么：

- 少了把扩展搜索词当核心锚点的漂移
- 少了弱 `rant` 的泛帖混入
- 少了假 `why_important`
- 少了脏 `competitor_mentions` 对页面的污染

## 验证

- `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_query_planner.py tests/services/hotpost/test_hotpost_retrieval_precision.py tests/services/hotpost/test_hotpost_detail_builder.py tests/services/hotpost/test_hotpost_response_bundle.py tests/services/hotpost/test_hotpost_quality_contract.py -q`
  - `31 passed`
- `npm --prefix hotpost-mini/hotpost-mini-app run build:weapp`
  - `Compiled successfully`

## 额外说明

- 我额外起了一个临时后端实例 `127.0.0.1:8026` 想跑真实 query。
- 结果确认两件事：
  1. 旧 query 会直接命中旧缓存，所以不能拿它判断新代码
  2. 临时实例只起了 API，没有挂当前代码的 worker，所以新 query 会停在 `queued`
- 因此这轮真实 query 验证还差最后一步：
  - 用当前代码 worker 跑一次无缓存 query

## 补充验证（8016 真联调链）

- 已重启：
  - `uvicorn app.main:app --host 0.0.0.0 --port 8016`
  - `celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=2 --queues=analysis_queue --hostname=analysis-live@hujiadeMacBook-Pro.local`
- 已清理 4 条旧 `rant` cache key，避免小程序继续命中旧结果。
- 验证：
  - `GET /api/v1/health` -> `{"status":"ok"}`
  - query=`why do tiktok videos get views but no purchases`
    - 最终返回 `degraded`
    - `query_planner` 已体现新契约：
      - `keywords=["tiktok","videos","get","views","but","purchases"]`
      - `expanded_terms=["issue","complaint","broken","refund","tiktok","videos"]`
    - `migration_intent=null`
    - `competitor_mentions=[]`
    - `top_quotes[].why_important=null`
- 这个结果说明：
  - 页面层“去假分析 / 去脏 migration”已经生效
  - 但 query/retrieval 还没到 100 分：
    - 弱英文问法仍可能把 `CustomerService` 之类弱相关帖子抓回来
    - 下一轮仍要继续收 `query translation / subreddit anchor / preview contract`
