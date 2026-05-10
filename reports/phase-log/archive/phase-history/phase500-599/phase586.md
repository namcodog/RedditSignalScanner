# Phase 586 - Rant 样本继续做厚，首轮检索改成更像 Reddit 的真实抱怨说法

## 本轮目标

在不碰 `trending / opportunity`、不新增新框架的前提下，继续把 `rant` 的样本做厚：

1. 让平台垂直社区更早进首轮主搜
2. 让第二条 query 不再像写给 AI 的长句，而更像 Reddit 里的真实抱怨短语

## 改动

### 1. `rant` 首轮社区继续收紧但更有力

- 文件：
  - `backend/app/services/hotpost/search_workflow.py`
  - `backend/config/hotpost_quality.yaml`
- 调整：
  - `rant + 商业转化语境` 下，如果已经识别出平台主词，会自动把：
    - `r/{platform}ads`
    - `r/{platform}shop`
    补进首轮候选社区
  - `ads` 也进入平台垂直社区加权
  - `rant.initial_subreddits_limit_by_mode` 从 `3` 提到 `4`

### 2. `rant` 第二条 query 改成紧凑问题短语

- 文件：
  - `backend/app/services/hotpost/query_planner.py`
- 调整：
  - 新增很薄的 `_compact_rant_problem_query()`
  - 只在“成交 / 购买 / 转化”语境下生效
  - 不再把第二条 query 固定成完整英文句子
  - 当前真实 query 会从：
    - `why tiktok content has traffic but no conversion to purchases`
    收成：
    - `tiktok no purchase conversion`

## 验证

### 自动化

- `python -m py_compile backend/app/services/hotpost/search_workflow.py backend/app/services/hotpost/query_planner.py ...`
  - 通过
- 定向：
  - `pytest test_hotpost_runtime_config.py test_hotpost_search_workflow.py -q`
  - `15 passed`
- 定向：
  - `pytest test_hotpost_query_planner.py test_hotpost_search_workflow.py test_evidence_collection_workflow.py -q`
  - `32 passed`
- 更宽 hotpost 回归：
  - `95 passed`

### 直接 Reddit 命中对照

对 `r/tiktokads / r/tiktokshop` 做了短 query 实测：

- `tiktok traffic no sales`
  - 在 `r/tiktokads` 命中较稳
- `tiktok no purchase conversion`
  - 在 `r/tiktokshop` 明显比完整英文句子更贴题
- `tiktok ads not converting`
  - 在 `r/tiktokads` 也能命中更直接的转化失败帖

这说明这轮主要收的是：

- 社区入口
- query 说法

而不是时间范围本身。

### live 无缓存

- query：
  - `为什么tiktok上做的内容有流量但却没有转化购买？`
- 结果：
  - `status=completed`
  - `mode_state=standard`
  - `summary=TikTok内容有流量却卖不动，商家开始怀疑继续投广告到底值不值。`
  - `evidence_count=5`
  - `communities=["TikTokAds","TikTokshop"]`
  - `subreddits=["r/tiktokads","r/tiktokshop","r/tiktok","r/tiktokmarketing"]`
  - `query_parts=["tiktok traffic no sales","tiktok no purchase conversion"]`

## 结论

这轮的意义很明确：

- `rant` 已经从：
  - `preview + 3 条证据`
  推进到：
  - `standard + 5 条证据`
- 样本变厚的主因不是放宽时间，而是：
  - 社区入口更像问题本身
  - query 说法更像 Reddit 用户会写的检索短语

## 剩余问题

现在主问题已经不是“没样本”，而是：

1. 首屏还会混进一两条偏 `help` 风格的弱价值帖子
2. `rant` 仍然缺“先怎么做”的闭环建议层

## 下一步

1. 继续压 `help / 求助式` 弱帖子排序
2. 开始补 `rant` 的动作建议闭环
3. 再进小程序验收最终成品感
