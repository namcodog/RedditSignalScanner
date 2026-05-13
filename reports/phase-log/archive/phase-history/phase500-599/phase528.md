# Phase 528 - Hotpost 算法层继续收口

## 背景

- Phase 527 已把 `opportunity` 的“假关键词命中”主问题钉死并收掉
- 当前剩余最影响成品感的两处：
  - `top_quotes` 代表性不稳定
  - `market_opportunity` 还不够硬

## 本轮执行

### 1. top_quotes 代表性算法收口

- `backend/app/services/hotpost/quality_contract.py`
  - `top_quotes` 不再只是“拿第一条 comment 或标题”
  - 新逻辑：
    - 优先选有信息量的 comment quote
    - 过滤：
      - moderator / 版规提醒
      - 太短评论
      - `Interested / same here` 这类低价值回复
    - 支持把 comment permalink 转成可点击 URL
    - 对 LLM 已产出的 `top_quotes` 与 fallback quotes 做 merge，再按质量排序

### 2. market_opportunity 硬结论投影

- `backend/app/services/hotpost/enrichment.py`
  - 基于 `unmet_needs` 补充：
    - `target_user`
    - `pricing_hint`
    - `gtm_channel`
    - 更具体的 `recommendation`
  - 逻辑仍保持轻量：
    - 不引入新模型
    - 不新增新链路
    - 只把已有 unmet need 翻成更像产品决策的表达

### 3. 测试

- `backend/tests/services/hotpost/test_hotpost_quality_contract.py`
  - 新增：
    - `test_apply_hotpost_quality_contract_replaces_weak_top_quotes_with_better_quotes`
- `backend/tests/services/hotpost/test_hotpost_enrichment.py`
  - 新增：
    - `test_enrich_opportunity_payload_fills_market_opportunity_from_top_need`

- 回归：
  - `pytest backend/tests/services/hotpost/test_hotpost_quality_contract.py backend/tests/services/hotpost/test_hotpost_enrichment.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
  - `18 passed`

## live 抽检说明

- 我做了 1 次最小 live 抽检，但命中了旧缓存：
  - `query = chargeback automation tool`
  - `query_id = a48dd4eb-270b-48a2-a88b-6075d0b0e278`
- 因为是缓存结果，里面仍保留旧版：
  - `Interested`
  - `target_user/pricing_hint = null`
- 这次 live **不能** 用来否定新算法，只能说明：
  - 线上缓存把旧结果复用了
- 为保护 Reddit API，本轮没有继续追加新的冷 query 强行撞 live。

## 结论

### 1. 发现了什么？

- 当前 Hotpost 剩余问题已经非常明确：
  - 是算法层收尾，不是架构层
  - 是“把已有证据投影得更值钱”，不是“再搞更复杂的系统”

### 2. 是否需要继续修复？

- 需要，但已经进入最后一小段
- 当前下一步最值得继续收的是：
  - `next_steps` 的动作硬度
  - `top_quotes` 在真实冷 query 下的最终表现

### 3. 下一步系统性计划

1. 下一轮若继续 live，只跑一条新的冷 `opportunity` query，专门验：
   - `top_quotes` 是否已摆脱低价值回复
   - `market_opportunity` 是否已补齐 `target_user/pricing_hint`
2. 如果 live 证明成立，就把 Hotpost 这条线收口
3. 不再继续扩 Hotpost 的工程复杂度

### 4. 这次执行的价值

- `top_quotes` 和 `market_opportunity` 都已经从“纯兜底/纯透传”升级成了轻量算法层
- 这一步把 Hotpost 真正推到了“剩下主要是最后一层产品打磨”的阶段
