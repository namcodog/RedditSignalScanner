# Phase 512 - Hotpost 第一刀：收口 quality contract，停止伪造核心洞察

## 本轮目标

按 Phase 511 的诊断，先执行第一刀：

- 不碰 query planner
- 不碰召回策略
- 不碰模型切换
- 先把 `quality_contract` 从“补分析”退回到“验分析”

核心原则：

- Hotpost 没产出核心洞察时，系统要诚实暴露缺口
- 不再让质量合同偷偷生成 `topics / pain_points / unmet_needs / market_opportunity`

## 已完成

### 1. `quality_contract` 停止补核心洞察

已修改：

- `backend/app/services/hotpost/quality_contract.py`

具体变化：

- `trending`
  - 不再自动从第一批帖子生成 `topics`
  - 保留 `trending_keywords`、`top_quotes`、`next_steps.suggested_keywords` 这类非核心展示补齐
- `rant`
  - 不再自动从第一条帖子生成默认 `pain_points`
- `opportunity`
  - 不再自动从第一条帖子生成默认 `unmet_needs`
  - 不再自动拼默认 `market_opportunity`

这意味着：

- 质量合同现在主要负责：
  - 保底通用展示字段
  - 检查缺口
  - 把缺口写入 `quality_contract_gaps`
- 不再负责替算法和 LLM 编结果

### 2. 测试口径已同步到“更诚实”的新真相

已修改：

- `backend/tests/services/hotpost/test_hotpost_quality_contract.py`
- `backend/tests/services/hotpost/test_hotpost_response_bundle.py`

测试新口径：

- trending 缺核心 topic 时，应直接暴露 `missing_topics`
- rant 缺 `pain_points` 时，应直接暴露 `missing_pain_points`
- opportunity 缺 `market_opportunity` 时，应直接暴露缺口并降级
- 不再断言“合同会自动补出一个默认分析”

## 验证结果

### 定向验证

```bash
cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_quality_contract.py tests/services/hotpost/test_hotpost_response_bundle.py -q
```

结果：

- `9 passed`

### Hotpost 回归

```bash
cd backend && SKIP_DB_RESET=1 pytest tests/services/hotpost tests/scripts/acceptance/test_run_hotpost_quality_smoke.py -q
```

结果：

- `89 passed`

## 当前判断

第一刀已经生效：

- Hotpost 现在更诚实了
- 核心洞察做不出来时，会直接降级并暴露缺口
- 后续终于可以分清：
  - 是 query/召回没找到对的数据
  - 还是 LLM/投影层没做出足够强的结构化结果

这一步的价值不在“结果看起来更漂亮”，而在：

- 后续提质可以基于真问题，而不是基于被兜底逻辑污染后的假问题

## 下一步

继续按既定顺序推进第二刀：

1. 补 query planner 合同
   - `query_intent`
   - `expanded_terms`
   - `negative_terms`
   - `candidate_subreddits`
   - `search_strategy`
2. 把 query planner 接进三模式主链
3. 再开始拆 recall 和 rank

## 一句话结论

Hotpost 现在已经迈出第一步：**质量合同不再伪造核心洞察**。
接下来终于可以在干净边界上，去真修 query 和召回。
