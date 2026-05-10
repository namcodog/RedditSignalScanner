# Phase 606 - 中文开放题路由补全并重新拿回 A_full

## 发现了什么？

- 这次 live 失败的根因不是 DB、语义库、也不是验收脚本，而是主链自己的 open-topic 通用模式没有把中文经营题补成英文 anchor。
- 原来的设计其实很清楚：
  - `topic_profile` 模式：靠英文 anchor 精准匹配
  - `open topic` 模式：靠通用关键词
- 真缺口是：
  - 中文经营题没有长出 `checkout / conversion / ecommerce` 这类英文 anchor
  - `build_open_topic_route(...)` 和 `semantic search` 都吃不到有效 query
- 另外还确认了一个运行事实：
  - `uvicorn --reload` 会自动吃到代码更新
  - 但 `celery analysis_queue` worker 不会
  - 所以修完代码后，必须显式重启 analysis worker，live 才会吃到新规则

## 是否需要修复？

- 需要，而且必须在主链内部修，不借 `hotpost`。

## 精确修复方法？

### 1. 新增 open-topic 中文经营题 anchor bridge

- 新增：
  - `backend/app/services/analysis/open_topic_anchor_bridge.py`
- 修改：
  - `backend/app/services/analysis/analysis_query_support.py`
- 口径：
  - 不直接造 query plan 兜底
  - 只把中文经营/交易表达补成英文 anchor
  - 让后续 `warzone classifier / Reddit search / semantic search` 继续按主链自己的规则工作
- 现在这类 query 会稳定长出：
  - `checkout`
  - `conversion`
  - `orders`
  - `sales`
  - `payment`
  - `compliance`
  - `trust`
  - `seller`
  - `ecommerce`

### 2. 收正关键词顺序

- `augment_keywords(...)` 不再把结果从 `set` 直接回 list
- 改成有序去重，避免 query 组合受随机顺序影响

### 3. 重启 analysis worker

- 原 live 进程没有自动吃到新代码
- 显式重启 `analysis_queue` worker 后，新的 open-topic route 才真正进入 live 主链

## 验证

### 定向测试

- `tests/services/analysis/test_analysis_query_support.py`
  - `8 passed`
- `tests/services/analysis/test_analysis_engine.py -k open_topic_route...`
  - `4 passed`

### 规则直验

- 对题目：
  - `卖成人用品时，最卡下单成交的地方是什么？`
- 当前代码直接输出：
  - `queries = ['checkout conversion orders', 'conversion orders sales', 'checkout conversion']`
  - `route.warzone = Ecommerce_Business`

### live 验收

- 执行：
  - `scripts/acceptance/run_open_question_live_acceptance.py --suite final --product-description '卖成人用品时，最卡下单成交的地方是什么？' --required-tier A_full`
- 结果：
  - `accepted = 1/1`
  - `report_tier = A_full`
- 结果文件：
  - `backend/reports/local-acceptance/open_question_live_final_1774868080.json`
- 当前命中社区：
  - `r/ecommerce`
  - `r/dropshipping`
  - `r/shopify`
  - `r/SaaS`

## 下一步系统性的计划是什么？

1. 把这条 open-topic 中文经营题路由补全写回文档与记忆。
2. 再挑 1~2 条不同领域开放题做复验，确认这不是单题偶然通过。
3. 然后继续收报告主链里剩余的质量问题，而不是再回头折腾底盘。

## 这次执行的价值是什么？达到了什么目的？

- 这次把真正卡住主链的最后一环找出来并修通了：
  - 不是底盘
  - 不是样本
  - 而是中文开放题没有被主链自己的规则正确理解
- 修完后，主链重新拿回真实 `A_full`，而且社区盘也回到了正确赛道。
