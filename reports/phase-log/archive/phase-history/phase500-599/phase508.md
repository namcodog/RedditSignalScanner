# Phase 508 - Hotpost 提质计划补全第一轮（P1 价值排序 + P2 模式专项强化）

## 时间
- 2026-03-27

## 目标
- 继续补齐 Hotpost 原提质计划里还没落完的 `P1 / P2`：
  - P1：证据价值排序、社区扩展策略
  - P2：`trending / rant / opportunity` 的模式专项强化
- 保持配置驱动、低耦合、高内聚，不做硬编码补丁。

## 执行内容

### 1) 配置层补齐 P1/P2 参数
- 更新：
  - `backend/config/hotpost_quality.yaml`
  - `backend/app/services/hotpost/hotpost_config.py`
- 新增配置：
  - `evidence_ranking`
    - relevance / quoteability / freshness / comments / signals 权重
    - `max_suggested_subreddits`
    - `opportunity_hint_priority`
  - `mode_insights`
    - trending：`explosive_hours / rising_days / sustained_days`
    - rant：`high_severity_percentage / medium_severity_percentage`
    - opportunity：`high_me_too_count / medium_me_too_count / wtp bonuses / workaround bonus`

### 2) P1：证据价值排序接入采集层
- 更新：
  - `backend/app/services/hotpost/evidence_collection_workflow.py`
- 新能力：
  - subreddit suggestion 不再只吃搜索返回，开始和 mode hints 混合：
    - `opportunity` 默认优先 niche hints
  - 证据不再只按抓取顺序入列，开始按“价值分”排序：
    - relevance
    - quoteability
    - freshness
    - comments
    - signals
  - 高价值证据会补充：
    - `why_relevant`
    - `why_important`

### 3) P2：trending 专项强化
- 更新：
  - `backend/app/services/hotpost/quality_contract.py`
- 新能力：
  - `time_trend` 不再只看分数/评论，开始结合时间窗口判断
  - `key_takeaway` 不再只是标题回填，而是带“为什么现在值得看”的说明句
  - 趋势语义补全为：
    - `explosive`
    - `rising`
    - `sustained`
    - `declining`

### 4) P2：rant / opportunity 专项强化
- 更新：
  - `backend/app/services/hotpost/enrichment.py`
- rant：
  - `pain_points` 按 mentions / percentage / voice 重新排序
  - 根据配置阈值推导 `severity`
  - 根据严重度给出更明确的 `business_implication`
- opportunity：
  - `unmet_needs` 按 me-too / workaround / willingness-to-pay 排序
  - 自动补 `demand_signal`
  - 自动补 `opportunity_insight`

## 测试与验证

### 定向验证
- 命令：
  - `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_runtime_config.py tests/services/hotpost/test_evidence_collection_workflow.py tests/services/hotpost/test_hotpost_enrichment.py tests/services/hotpost/test_hotpost_response_bundle.py -q`
- 结果：
  - `15 passed`

### Hotpost 全回归
- 命令：
  - `cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost tests/scripts/acceptance/test_run_live_hotpost_acceptance.py -q`
- 结果：
  - `98 passed`

## 当前结论
- 这轮已经把原计划里最关键的 `P1 / P2` 底座补强拉起来了：
  - 证据开始按价值排序，不再只按热度或抓取顺序
  - `opportunity` 社区扩展开始偏向更相关的 niche hints
  - `trending / rant / opportunity` 都有了第一版专项强化逻辑

## 还没完全补完的点
- query rewriter 还没有正式输出 `expanded_terms / rejected_terms` 这类可观测结构
- “三模式各 3 条黄金样题”还没有正式固化成标准样题库
- 真实 `acceptance-hotpost-quality-smoke` live 还没跑
- 主观验收表（30 秒看懂 / 值不值 / 下一步）还没固化

## 五问回顾
1. 发现了什么？
- 之前 Hotpost 虽然已经有质量合同和自动补证，但证据排序和模式专项判断仍然偏弱，容易让结果“有料但不够值钱”。

2. 是否需要修复？
- 需要，而且应该继续在 Hotpost 域内做，不需要把其他主链一起改动。

3. 精确修复方法？
- 用配置驱动证据排序和模式专项阈值；
- 把价值排序接到 evidence collection；
- 把趋势判断、痛点严重度、机会排序接到 contract / enrichment。

4. 下一步系统性计划是什么？
- 跑真实 `make acceptance-hotpost-quality-smoke` 看 live 数据表现；
- 再补 query rewriter 的 `expanded_terms / rejected_terms`；
- 最后固化黄金样题和主观验收表。

5. 这次执行的价值是什么？达到了什么目的？
- Hotpost 不再只是“结构完整”，而是开始朝“证据更对、排序更值钱、模式判断更像产品结论”推进。
