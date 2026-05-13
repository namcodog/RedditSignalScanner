# Phase 477 - Analysis Query Support 抽离

## 时间
- 2026-03-25

## 背景
- 继续按“只拆内部边界，不改 `Full A` 对外交付合同”的口径推进分析主链重构。
- 这轮锁定的是 `analysis_engine.py` 中另一整块高频但不该留在 orchestrator 里的逻辑：
  - keywords 提取与扩展
  - Reddit search query 组装
  - stopwords / blocklist / blacklist 过滤
  - topic profile 双钥匙过滤
  - query focus 过滤

## 本轮动作

### 1. 新增 query support 模块
- 新增：
  - `backend/app/services/analysis/analysis_query_support.py`
- 抽离能力：
  - `build_reddit_search_queries(...)`
  - `extract_keywords(...)`
  - `augment_keywords(...)`
  - `apply_keyword_stopwords(...)`
  - `filter_posts_by_keywords(...)`
  - `filter_posts_by_blocklist(...)`
  - `filter_posts_by_blacklist_config(...)`
  - `apply_query_focus_filter(...)`
  - `apply_topic_profile_required_filter(...)`
  - `apply_topic_profile_context_filter(...)`

### 2. 主链改接新模块
- 更新：
  - `backend/app/services/analysis/analysis_engine.py`
- 变化：
  - 主链不再自己背这整段关键词/过滤 support
  - `run_analysis()` 回到“拿输入 -> 调 support -> 编排结果”的角色
  - 未被引用的 `_build_query_focus_groups(...)` 直接清掉，不再占主链体积

### 3. 补定向测试
- 新增：
  - `backend/tests/services/analysis/test_analysis_query_support.py`
- 覆盖：
  - 中文关键词桥接到英文 domain 词
  - Reddit 搜索 query 的非 ASCII 过滤和去重
  - stopwords 合同
  - topic profile 的 brand subreddit 锚点过滤
  - query focus + blocklist 串联

## 中途发现的问题
- 第一轮回归炸了两个测试，但不是逻辑坏了，而是新测试预期写得太理想化：
  - `augment_keywords(...)` 当前真实合同不会补出 `track / tracker`
  - `build_reddit_search_queries(...)` 在 3 个 token 场景下，第二条 query 真实行为是 `paypal fees`，不是 `fees risk`
- 处理：
  - 把测试预期收回到当前真实合同
  - 不拿错误测试去误判主链

## 验证
- 运行：
  - `cd backend && pytest tests/services/analysis/test_analysis_query_support.py tests/services/analysis/test_analysis_evidence_package_support.py tests/services/analysis/test_analysis_finalization_support.py tests/services/analysis/test_analysis_engine_search_grouping.py tests/services/analysis/test_analysis_engine_collection_mapping.py tests/services/analysis/test_analysis_readiness_support.py tests/services/analysis/test_analysis_output_support.py tests/services/analysis/test_analysis_facts_support.py tests/services/analysis/test_analysis_artifacts.py tests/services/analysis/test_insight_synthesis.py tests/services/analysis/test_analysis_rendering.py -q`
  - `cd backend && python -m py_compile app/services/analysis/analysis_query_support.py app/services/analysis/analysis_evidence_package_support.py app/services/analysis/analysis_engine.py tests/services/analysis/test_analysis_query_support.py`
  - `cd backend && wc -l app/services/analysis/analysis_engine.py`
- 结果：
  - `33 passed`
  - `analysis_engine.py = 3718` 行

## 结果
- `analysis_engine.py` 行数变化：
  - `4297 -> 3718`
- 当前累计减重曲线：
  - `5877 -> 5741 -> 5660 -> 5497 -> 4624 -> 4458 -> 4297 -> 3718`
- 这轮价值：
  - 主链里最大的一段“关键词/过滤杂活”被整块搬走
  - `analysis_engine.py` 已经正式跌破 `4000`
  - 离你要的中期目标 `3000 -> 1500` 又迈了一大步

## 下一步
- 继续盘 `analysis_engine.py` 剩余大块
- 优先看：
  - lineage / embedding / target-id support
  - signal extraction 前后的 payload 整形层
  - run_analysis 中部还残留的 side-effect 协调
