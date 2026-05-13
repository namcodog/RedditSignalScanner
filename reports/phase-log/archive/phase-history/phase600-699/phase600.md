# Phase 600 - Rant 商业阻力底座继续收口：切断 LLM 覆盖、移除 other、非平台经营 query 优先 business challenges

## 1. 发现了什么？

这轮把 `rant` 新底座继续往前推时，抓到了 3 个真正影响 live 结果的漏口：

1. `response_bundle` 里，LLM 还能整组覆盖 `pain_points`
   - 前面虽然已经把 `rant` 的商业阻力分类接进来了
   - 但 `merge_hotpost_llm_report(...)` 还会把旧的 LLM `pain_points` 整组盖回 payload
   - 结果就是第一条痛点像新脑子，第二条还会退回旧类目
2. `other` 这种无意义分类会被直接端上屏
   - 这会把“未识别”伪装成“一个真的痛点”
   - 属于典型的“正确的废话”
3. 非平台经营型 query 还在被过早压成 `no sales`
   - `卖成人用品时，最卡下单成交的地方是什么？`
   - 之前会先走 `sex toys no sales`
   - 导致召回太窄，还会诱发奇怪社区扩展

## 2. 是否需要修复？

需要。

而且这轮修的是 `rant` 的算法边界，不是工程层补壳：

- `pain_points` 谁说了算
- 哪种 query 先宽搜、哪种 query 先窄搜
- 哪些“没分类出来”的结果应该干脆别上屏

这三刀都只作用在 `rant`，不碰 `trending` 主链。

## 3. 精确修复方法？

### 3.1 切断 LLM 对 `rant pain_points` 的覆盖权

文件：

- `backend/app/services/hotpost/response_bundle.py`

修复：

- `rant` 下，`pain_points` 只认本地商业阻力聚类结果
- LLM 继续负责：
  - `summary`
  - `top_quotes`
  - `post_annotations`
- 但不再负责改写 `pain_points`

这一步把 `rant` 的职责边界钉死了：

- 分类 = 算法
- 表达补充 = LLM

### 3.2 不再把 `other` 当成可展示痛点

文件：

- `backend/app/services/hotpost/hotpost_runtime.py`

修复：

- `build_hotpost_pain_points(...)` 现在会直接隐藏 `other`
- 只要已经识别出真实商业阻力，就不再把 `other` 也端上屏

结果是：

- `weak_buy_reason`
- `transaction_friction`
- `identity_friction`

这种有意义的类目会保留，`other` 不再抢位置。

### 3.3 平台垂直社区扩展不再误伤普通商品词

文件：

- `backend/app/services/hotpost/search_workflow.py`

修复：

- `r/{primary}ads`
- `r/{primary}shop`

这种扩展现在只在“真的存在平台 seed 社区”时才会发生。

也就是：

- `r/tiktok` / `r/tiktokhelp` 这类平台 seed 存在时，允许扩展 `r/tiktokads`
- `r/sextoys` 这种商品社区，不会再因为包含 `toys` 就扩成 `r/toysads`

### 3.4 非平台经营型 query 优先走 business challenges

文件：

- `backend/app/services/hotpost/query_planner.py`

修复：

- 对非平台经营型 `rant`
- 如果识别到是“这门生意本身卡住了”
- `query_parts` 会优先把：
  - `adult toys sales business challenges`
  放到前面
- 然后再补更窄的：
  - `adult toys no sales`

这一步的价值是：

- 先厚样本
- 再抓更窄的成交信号

而不是一上来就把检索面压死。

### 3.5 新增验证

文件：

- `backend/tests/services/hotpost/test_hotpost_response_bundle.py`
- `backend/tests/services/hotpost/test_hotpost_runtime.py`
- `backend/tests/services/hotpost/test_hotpost_search_workflow.py`
- `backend/tests/services/hotpost/test_hotpost_query_planner.py`

新增约束：

- `rant` 的 deterministic `pain_points` 必须压过 LLM 旧类目
- 混合分类时 `other` 不得上屏
- 平台扩展只允许在真实 platform seed 存在时触发
- 非平台经营痛点 query 必须优先走 `business challenges`

## 4. 验证

### 测试

执行：

```bash
cd backend && SKIP_DB_RESET=1 ../.venv/bin/pytest tests/services/hotpost -q
```

结果：

- `185 passed`

### Live backend 验证

后端实例：

- `uvicorn app.main:app --host 0.0.0.0 --port 8016`

#### Query 1

- `卖成人用品时，最卡下单成交的地方是什么？`

结果：

- `status=completed`
- `mode_state=standard`
- `evidence_count=24`
- `communities=["ecommerce","Entrepreneur","smallbusiness"]`
- `query_parts=["adult toys sales business challenges","adult toys no sales"]`
- `subreddits=["r/ecommerce","r/sextoys","r/smallbusiness","r/entrepreneur"]`

前 3 条痛点：

1. `为什么人看了不买 / weak_buy_reason`
2. `为什么成交卡在交易环节 / transaction_friction`
3. `为什么用户想要却下不了手 / identity_friction`

这说明：

- 样本已经不再被压成一条孤证
- 结果开始回到“购买理由 / 交易摩擦 / 羞耻与私密”这种商业阻力语言

#### Query 2

- `为什么TikTok内容有曝光却还是卖不出去？`

结果：

- `status=completed`
- `mode_state=standard`
- `evidence_count=24`
- `communities=["TikTokAds","TikTokshop","TikTok"]`

前 2 条痛点：

1. `为什么人看了不买 / weak_buy_reason`
2. `为什么成交卡在交易环节 / transaction_friction`

当前确认：

- `other` 已不再上屏
- `下一步` 也不再出现 `先处理 other` 这种废话

#### Query 3

- `trending: shopify chargeback evidence response workflow toolset`

结果：

- `status=degraded`
- `mode_state=no_hit`
- `evidence_count=0`

当前判断：

- `trending` 这轮没有被 `rant` 改动误伤
- 但它自己的冷启动质量仍是老问题，和这轮 `rant` 收口无关

## 5. 这次执行的价值是什么？达到了什么目的？

这轮最大的价值，不是“又加了几个规则”，而是把 `rant` 更像样地收成了一条独立的商业阻力链：

1. `pain_points` 不再一半算法、一半 LLM 抢话语权
2. `other` 不再冒充痛点
3. 非平台经营型问题，终于开始优先搜“这门生意难在哪”
4. `成人用品` 这类 query 已经从脆弱的单帖孤证，推进到有样本、有层次的 `standard` 结果

当前可以下的判断：

- `TikTok 卖不动` 这条后端结果已经达到可验收状态
- `成人用品` 这类经营型 `rant` 也已经明显回到正确方向
- 下一步如果继续打，应该优先收：
  - 成人用品这类 query 的排序纯度
  - 不再让泛卖货帖占掉前排
