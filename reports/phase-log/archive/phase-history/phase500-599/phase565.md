# Phase 565 - Hotpost Rant 模式全链路深诊断

## 发现了什么？
- 这次不是某一个 bug，而是 `rant` 整条链已经出现**工作流级漂移**。
- 当前 `rant` 不是一个被完整打磨的独立模式，更像是：
  - 入口转译放宽了
  - 检索精度对 `rant` 不够严
  - 后端 fallback 结构仍很早期
  - 页面又把弱结果和系统术语直接暴露给用户
- 因此用户看到的不是“分析不够深”，而是：
  - 入口 query anchor 宽
  - 中间候选帖偏题
  - 上屏区块拿错层
  - 文案还在硬包装

## 关键实证

### 1. 中文 query 转译契约已经漂了
- 原文档口径：
  - `docs/Reddit爆帖速递_产品模块文档.md`
  - 中文输入应先被解析成 **英文 query + 英文关键词 + 英文社区**
- 原测试口径：
  - `backend/tests/services/hotpost/test_hotpost_query_resolver.py`
  - 期望 `keywords` 是类似：
    - `["Roomba", "robot vacuum"]`
  - 也就是**核心锚点词**，不是扩展搜索短语
- 当前 live resolver 实测：
  - `search_query` 正常
  - 但 `keywords` 返回的是：
    - `tiktok traffic no sales`
    - `tiktok high views low conversions`
    - `tiktok content no purchases`
    - `tiktok marketing funnel`
    - ...
  - 这说明当前 resolver prompt 允许模型直接输出**扩展搜索短语**
- 后果：
  - `query_planner` 把这些长短语当成 `core_terms`
  - 后续 `domain_terms / query_parts / retrieval focus` 一起被拉宽
  - `rant` 入口语义已经不再是“问题锚点”，而是“半成品搜索建议”

### 2. retrieval 对 rant 不够严格
- 当前 `retrieval_precision.py` 的严格未知源过滤，主要是给 `opportunity` 做的。
- `rant` 当前即使：
  - 落在 unknown 社区
  - 没有 visible domain hits
  - 没有强 direct hits
  也仍可能保留下来，只要没被硬 block。
- 当前真实 case：
  - query：`为什么tiktok上做的内容有流量但却没有转化购买?`
  - 最终结果里大量 `r/marketing` 泛帖进入前排
  - 真正相对贴题的 `r/TikTok` 证据被压到很后面
- 这说明：
  - `rant` 当前没有做到“偏题就别进”
  - 只是“偏题也能进，只是 reason 写得难看一点”

### 3. 候选排序仍然偏热度，不够偏问题证据
- `evidence_collection_workflow.py`
  - `_build_value_signals`
  - `_build_candidates`
  - `candidates.sort(...)`
- 当前 `value_score` 仍大量吃：
  - quoteability
  - freshness
  - comments
  - signal_count
- 在入口锚点已经放宽的情况下：
  - 高热度泛营销帖
  - 会压过低热度但强相关的真实 TikTok 转化抱怨
- 真实结果里就出现：
  - 前几条是 SEO / LinkedIn / Facebook Ads / MrBeast / email marketing
  - 真正贴题的 TikTok 抱怨帖只出现在 `pain_points[0].evidence_posts`

### 4. 页面代表帖子拿错层了
- 当前 `friction` 页面代表帖子区展示的是：
  - `data.top_posts`
- 但当前结果里真正贴题的证据，其实已经存在于：
  - `pain_points[0].evidence_posts`
- 这意味着页面把“全局排序前几条”端给了用户，而不是把“支撑 pain point 的证据帖”端给用户。
- 结果就是：
  - 页面看起来像完全跑题
  - 即使后端局部已经抓到相对对的帖子，用户也看不到

### 5. migration / competitor 仍然是脏源
- 虽然之前已经清洗过 `migration_intent.destinations`
- 但页面当前实际展示的不是 `destinations`
- 而是 `competitor_mentions`
- 后端 fallback `extract_competitor_mentions()` 仍然过松：
  - 当前实测能产出：
    - `reading`
    - `product`
    - `seeing`
    - `the`
- 所以这块不是“文案不好”，而是上游结构仍然脏。

### 6. rant 质量合同还没有真正成形
- `quality_contract.py`
  - `_ensure_rant_contract()` 现在是空实现
- `mode_contract.py`
  - preview 态只会 trim：
    - `pain_points`
    - `top_quotes`
  - 不会自动收掉：
    - `top_posts`
    - `competitor_mentions`
    - `next_steps`
- 所以 preview/noisy 场景下，用户仍会看到一整页“像完整结果”的弱内容。

### 7. AI 味的根源不是一个 prompt，而是多层 fallback 在冒充分析
- `evidence_collection_workflow.py`
  - `why_important` fallback 仍是：
    - `评论活跃`
    - `最近讨论升温`
    - `信号密度更高`
- `friction/helpers.ts`
  - `postInterpretation()` / `quoteInterpretation()` 在拿不到真正解释时，会自动补模板话术
- `detail_builder.py`
  - `build_top_rants()` 甚至把 `why_relevant` 直接塞给 `why_important`
- 所以当前 AI 味不是“模型不够像人”
- 而是：
  - 当真正分析缺席时，系统会用模板化占位语硬顶上去

## 是否需要修复？
- 需要，而且不应该再按“补点”推进。
- 当前正确口径不是继续 patch，而是把 `rant` 当成独立模式重新定义：
  1. 入口语义契约
  2. retrieval gate
  3. evidence ranking
  4. representative evidence selection
  5. migration/competitor contract
  6. preview 展示策略
  7. 去 AI 味表达规则

## 100 分标准下的完整重构方向
1. **重写中文 query 解析合同**
   - `keywords` 只能返回核心英文锚点词
   - 不允许返回完整搜索短语列表
   - 搜索建议应是另一字段，不可污染 `keywords`
2. **把 rant retrieval 变成“强问题锚点模式”**
   - unknown 社区 + 无 visible domain hit + 无强 direct hit 时直接丢弃
   - 重新恢复“有讨论门槛”的硬过滤，而不是只加分
3. **把代表帖子改成 evidence-backed**
   - 页面优先展示 `pain_points[].evidence_posts`
   - 不再直接展示 `top_posts[:N]`
4. **彻底切断 competitor fallback 对页面的污染**
   - `flow/替代` 只允许稳定目的地上屏
   - 没有稳定迁移证据时直接隐藏此区块
5. **为 rant 建真正的质量合同**
   - `_ensure_rant_contract()` 不再留空
   - preview/no_hit 时主动收掉弱区块
6. **去 AI 味**
   - 禁止模板性 fallback 直接面向用户
   - 没有真正解释，就显示“还不能下判断”
   - `why_important` 必须回答“暴露了什么问题”，而不是“这条很活跃”

## 下一步系统性计划
1. 先冻结当前 `rant` 现状，形成一版“目标工作流蓝图”
2. 重新定义：
   - query contract
   - retrieval contract
   - rant result contract
   - UI projection contract
3. 再按蓝图分层重做，不再 patch 式推进

## 这次执行的价值是什么？
- 这轮已经证明：
  - `rant` 低分不是因为模型单点差
  - 而是模式级契约已经漂了
- 现在可以停止“补一块又冒一块”的循环，转为真正的独立模式重构。
