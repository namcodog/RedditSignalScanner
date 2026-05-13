# Phase 611 - Hotpost Rant Evidence Judge 第一轮收口

## 时间
- 2026-03-30 21:42:00 CST

## 发现了什么
- 这轮不是继续补 `TikTok` 个案，而是把 `platform conversion rant` 这整个 family 的排序纯度往前推了一刀。
- 之前最典型的脏前排，不是完全不相关，而是这类帖子：
  - 标题里有 `no sales`
  - 但正文其实是在求人帮忙、找人审广告、找 agency
  - 它们会挤占真正能解释“为什么流量不成交”的证据位
- 这轮 live 也暴露出新的剩余不确定性：
  - family 已经分对了
  - query parts 也在对的语境里
  - 但 uncached live 下，当前环境会出现：
    - `communities=[]`
    - `top_titles=[]`
  - 同时 `uvicorn` 日志里出现了 `aiohttp` 走 HTTPS proxy 的 runtime warning
  - 说明当前剩余风险更像：
    - live acquisition / 外网代理条件
  - 而不是：
    - `ProblemFrame`
    - family contract
    - summary contract

## 是否需要修复
- 需要，但下一步不该回去补 prompt、页面或单题规则。
- 当前应该把剩余问题明确归类成：
  1. `evidence judge` 已经开始收口
  2. `live acquisition stability` 仍需单独验证

## 精确修复方法
- 修改：
  - `backend/app/services/hotpost/retrieval_precision.py`
- 新增 / 更新测试：
  - `backend/tests/services/hotpost/test_hotpost_retrieval_precision.py`
  - `backend/tests/services/hotpost/test_evidence_collection_workflow.py`

### 本轮算法调整
- 只对 `query_family = platform_conversion_friction` 生效：
  - 如果帖子同时命中：
    - 转化/销售损失词
    - 平台商业词（`ads/shop/seller/store/merchant`）
  - 则提升排序分
- 如果帖子正文更像：
  - `need help`
  - `reach out`
  - `dm me`
  - `looking for help`
  - `agency`
  这类求助/找人救火语境
  - 则显式降权

### 这次没有做的事
- 没有新增平台名单 patch
- 没有新增泛社区兜底
- 没有改页面文案
- 没有把 fallback 再塞回结果层

## 验证
- 定向回归：
  - `SKIP_DB_RESET=1 pytest tests/services/hotpost/test_hotpost_retrieval_precision.py tests/services/hotpost/test_evidence_collection_workflow.py tests/services/hotpost/test_hotpost_search_workflow.py -q`
  - `44 passed`
- 全量 hotpost：
  - `SKIP_DB_RESET=1 pytest tests/services/hotpost -q`
  - `213 passed`
- `py_compile`：
  - `retrieval_precision.py`
  - `evidence_collection_workflow.py`
  - 通过

## live smoke
- query:
  - `why are tiktok views no longer converting into orders?`
- 结果：
  - `from_cache=false`
  - `status=completed`
  - `query_family=platform_conversion_friction`
  - `candidate_subreddits=["r/tiktok","r/tiktokads","r/tiktokshop","r/tiktokhelp"]`
  - `query_parts=["tiktok ads no sales","tiktok orders low conversion"]`
  - `summary=TikTok内容有流量却卖不动，商家开始怀疑继续投广告到底值不值。`
  - 但当前 `communities=[] / top_titles=[]`

- query:
  - `why do tiktok ads get clicks but still no sales?`
- 结果：
  - `from_cache=false`
  - `status=completed`
  - `query_family=platform_conversion_friction`
  - `mode_state=preview`
  - 当前 `communities=[] / top_titles=[]`

## 当前结论
- 这轮已经证明：
  - `platform conversion rant` 的 family contract 没漂
  - `evidence judge` 的第一刀已经落到测试和代码里
- 当前真正剩余的不确定性，已经不再是：
  - 问题理解错了
  - summary 写歪了
- 而是：
  - live acquisition 在当前环境下不稳定
  - 导致“入口对了，但样本拿不回来”

## 下一步系统性的计划
1. 不回头补 prompt / 页面 / 单题规则
2. 单独定位：
   - `live acquisition / proxy / community fetch` 稳定性
3. 在 acquisition 稳定后，再继续验：
   - `platform conversion rant` 的前排纯度

## 这次执行的价值是什么
- 这轮最大的价值，不是“结果更好看了”，而是把剩余问题继续往下收窄了：
  - 不是 family 漂了
  - 不是排序 contract 漂了
  - 而是 live 采集层在当前环境里仍然不稳定
- 这能防止下一轮又误回：
  - 补 prompt
  - 补页面
  - 补单题
