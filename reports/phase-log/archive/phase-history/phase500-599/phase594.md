# Phase 594 - Rant 经营型 query 深诊断与算法纠偏

## 本轮目标
- 深挖 `售卖成人小玩具都有什么痛点?` 这类经营型 `rant` 为什么会明显变薄。
- 不做工程化扩张，只收 `query -> retrieval -> explanation` 三层算法。

## 主要发现
- 这类 query 之前不是单点坏，而是 4 个问题叠在一起：
  1. `query resolver` 会把中文直译成 `pain points selling ...` 这种生硬英文，缺少经营侧锚点。
  2. `query planner` 只要吃到一个垂直社区，就会把默认 business 社区入口丢掉，结果极不稳定。
  3. `response_bundle` 里有真实误判：
     - `adult` 里的 `ad` 会误触发“投流/广告”解释。
     - `buy` 这类过宽词会把一般购买语境误当成“转化/成交问题”。
  4. `rant` 对经营型痛点过度依赖“抱怨口吻”，导致很多强直命中的 founder/business 帖会被门口直接挡掉。

## 本轮落地
- `backend/app/services/hotpost/query_resolver.py`
  - 收紧中文转英文合同：
    - “卖某类产品/做某类生意有什么痛点”优先转成经营侧 Reddit 搜索短语
    - 不再鼓励直译成 `pain points selling ...`
- `backend/app/services/hotpost/query_planner.py`
  - `rant` 新增经营型 query 压缩：
    - `adult sex toys business challenges`
    - `selling adult toys challenges`
  - 去掉 `pain / points / challenges` 这类空锚点
  - 去掉 `shipping / policy / restrictions` 这类 meta 词对主 query anchor 的污染
  - 对经营型 `rant` 即使已解析出垂直社区，也继续保留：
    - `r/smallbusiness`
    - `r/ecommerce`
    - `r/entrepreneur`
  - 不再把 `r/customerservice / r/rant` 混进经营型默认入口
- `backend/app/services/hotpost/evidence_collection_workflow.py`
  - 给经营型 `rant` 开了一条很窄的“强直命中也能进”通道：
    - 帖子就算不带典型 rant 词
    - 只要 query 属于经营型问题
    - 且 direct hit 足够强
    - 也能保留下来
- `backend/app/services/hotpost/response_bundle.py`
  - 修掉 `adult -> ad` 误判
  - 去掉 `buy / buys / bought` 这类过宽成交信号
  - 新增两类更准的帖子解释：
    - 广告渠道/合规受限
    - 品牌形象与真实人群脱节
  - `rant` 里只要 deterministic `why_important` 能明确判断，就优先覆盖 LLM 的错解释

## 测试
- `SKIP_DB_RESET=1 pytest backend/tests/services/hotpost/test_hotpost_response_bundle.py backend/tests/services/hotpost/test_hotpost_query_planner.py backend/tests/services/hotpost/test_evidence_collection_workflow.py -q`
  - `42 passed`
- `python -m py_compile backend/app/services/hotpost/query_resolver.py backend/app/services/hotpost/query_planner.py backend/app/services/hotpost/evidence_collection_workflow.py backend/app/services/hotpost/response_bundle.py`
  - 通过

## Live 结果
- 真实无缓存 query：
  - `售卖成人小玩具都有什么痛点?`
- 当前较稳定的一次结果：
  - `query_id=b6ed06e6-2eb6-4cd9-b825-e8eaea48a692`
  - `from_cache=false`
  - `status=completed`
  - `mode_state=standard`
  - `summary=这类讨论暴露的不是单点运营问题，而是行业默认品牌形象和真实用户人群本身就脱节。`
  - `evidence_count=16`
  - `candidate_subreddits=["r/sextoys","r/smallbusiness","r/ecommerce","r/entrepreneur"]`
  - `subreddits=["r/sextoys","r/smallbusiness","r/ecommerce","r/entrepreneur"]`
  - `pain_points=["品牌与营销困境","合规与运营模糊"]`

## 当前结论
- 这轮已经确认：
  - 经营型 `rant` 之前确实被“翻译生硬 + 社区入口不稳 + 解释误判 + 口吻门槛过死”四层一起拖垮。
- 这轮已经拿到的真实收益：
  - query 不再是 `pain points selling ...`
  - business 社区入口开始稳定保留
  - `adult -> ad` 这类离谱误判已经被修掉
  - 经营型 founder/business 帖不会再因为不够“像抱怨帖”被一刀砍掉
- 但还没过线的地方也很明确：
  - 排序里还会混进明显偏题的帖子，例如 `selling crabs`
  - 这说明下一轮该打：
    - 经营型 `rant` 的排序纯度
    - 行业痛点 vs 泛创业帖 的区分
