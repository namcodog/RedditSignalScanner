# Phase 474 - Analysis Collection / Routing Support 抽离

## 背景

在完成 readiness support 抽离之后，`analysis_engine.py` 里还残留一大块高耦合内容：

- 开放题 warzone 路由
- 静态社区池与 seed 社区
- 社区选择与模式过滤
- 缓存 / API / cache-only 采集 support
- collection result 到内部 payload 的映射

这块既大又杂，而且同时承担了“路由、选社区、采集支撑、数据形状归一”四种职责，是继续减重主链必须啃掉的一块大骨头。

## 本轮改动

### 1. 新增 collection support 模块

- 文件：`backend/app/services/analysis/analysis_collection_support.py`

新增并承接：

- 数据模型：
  - `InsufficientDataError`
  - `CommunityProfile`
  - `OpenTopicRoute`
  - `CollectedCommunity`
- 社区归一与搜索分组：
  - `normalise_community_name(...)`
  - `group_search_posts_by_selected_subreddit(...)`
- 开放题路由：
  - `build_open_topic_route(...)`
  - `filter_communities_for_open_topic_route(...)`
  - `open_topic_route_allows_name(...)`
- 社区池与采集 support：
  - `COMMUNITY_CATALOGUE`
  - `select_top_communities(...)`
  - `filter_communities_by_mode(...)`
  - `collect_data(...)`
  - `backfill_cache_misses(...)`
  - `build_data_collection_service(...)`
  - `collection_from_result(...)`
  - `try_cache_only_collection(...)`
  - `reddit_post_to_dict(...)`
- 采集周边：
  - `build_collection_warnings(...)`
  - `check_trend_views_freshness(...)`
  - `fetch_coverage_summary(...)`
  - `community_pool_priority_order(...)`

### 2. 收窄 `analysis_engine.py`

- 文件：`backend/app/services/analysis/analysis_engine.py`

当前已从主链里搬走：

- route / seed / static catalogue
- community selection / mode filter
- collection result mapping
- cache-only collection
- coverage / trend freshness support

主链现在保留这些名字的导入别名，以保持对外测试接缝和产品合同不变，但内部实现已经不再留在 God Object 里。

## 验证

通过：

- `cd backend && pytest tests/services/analysis/test_analysis_engine_search_grouping.py tests/services/analysis/test_analysis_engine_collection_mapping.py tests/services/analysis/test_analysis_readiness_support.py tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py -q`
- `cd backend && python -m py_compile app/services/analysis/analysis_collection_support.py app/services/analysis/analysis_engine.py`

## 结果

- `analysis_engine.py` 从 `5497` 行降到 `4624` 行
- 单轮净减 `873` 行
- 这是当前重构里最大的一次减重
- 当前 analysis 侧分层继续变清楚：
  - collection / routing support
  - evidence selection
  - evidence ledger
  - insight synthesis
  - analysis facts support
  - analysis output support
  - analysis readiness support
  - analysis artifacts

## 下一步

- 继续盘 `analysis_engine.py` 剩余大块
- 优先看：
  - render 前置编排
  - sources / confidence 相关 support
  - 还有没有主链里残留的质量门禁与结果装配杂活
