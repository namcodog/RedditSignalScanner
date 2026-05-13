# Phase 612 - Hotpost Rant 平台转化类排序纯度第二轮收口

## 时间
- 2026-03-30 22:10:00 CST

## 这轮解决了什么
- 继续只打 `platform conversion rant` 这一类问题，不补 prompt，不补页面，不补单题。
- 这轮把一个关键问题彻底收掉了：
  - 之前 `platform conversion` 前排里，仍会混进“成交后履约/诈骗”类帖子
  - 例如：
    - 订单取消了却又送到了
    - 包裹像骗局
  - 这种帖子虽然是交易问题，但解释不了：
    - 为什么广告有点击却不出单
- 现在这类帖子不再只是“排后面”，而是会被当成 **错误生命周期阶段的噪音** 直接筛掉。

## 本轮改动

### 1. 执行层
- `backend/app/services/infrastructure/reddit_client.py`
  - `aiohttp.ClientSession(..., trust_env=False)`
  - 目的：
    - 让 Reddit 采集不再静默继承宿主机代理环境
    - 避免 live acquisition 被环境代理污染

### 2. family 级 evidence judge
- `backend/app/services/hotpost/retrieval_precision.py`
  - 为 `platform_conversion_friction` 增加“交易前 / 交易后”阶段区分：
    - 交易前转化词：
      - `click`
      - `conversion`
      - `tracking`
      - `pixel`
      - `checkout`
      - `cart`
      - `landing page`
      - `offer`
    - 交易后噪音词：
      - `refund`
      - `shipping`
      - `delivery`
      - `package`
      - `cancelled order`
      - `scam`
  - 规则：
    - 交易前转化问题 -> 加权
    - 交易后履约/诈骗问题，且不带交易前信号 -> 直接剔除

## 验证

### 定向回归
- `tests/services/infrastructure/test_reddit_client_proxy.py`
- `tests/services/hotpost/test_hotpost_retrieval_precision.py`
- `tests/services/hotpost/test_evidence_collection_workflow.py`
- 结果：
  - `30 passed`

### 全量回归
- `tests/services/hotpost`
- `tests/services/infrastructure/test_reddit_client_proxy.py`
- 结果：
  - `216 passed`

## live 验证
- query（未缓存）：
  - `why do tiktok ads get clicks but still no sales now <random>?`

### 这轮之前
- `raw_posts = 118`
- `filtered_posts = 2`
- 前排里还混着：
  - `cancelled my order but it still came and it was a scam`

### 这轮之后
- `from_cache=false`
- `query_family=platform_conversion_friction`
- `raw_posts = 118`
- `filtered_posts = 1`
- 最终前排只剩：
  - `TikTok Ads not tracking clicks`

## 当前结论
- 这轮已经把 `platform conversion rant` 的排序纯度继续往前推进了一大步：
  - 不再把“成交后噪音”误当成“成交前转化阻力”
- 到这个阶段可以明确说：
  - `ProblemFrame` 没漂
  - family 没漂
  - `evidence judge` 也开始真正按商业阶段工作了

## 下一步
- 继续保持同一原则：
  - 不补单题
  - 不补页面
  - 不补兜底
- 后面该继续做的是：
  - 扩 `platform conversion rant` 的 benchmark 覆盖面
  - 再抽不同平台 / 不同表达方式做 live 验证

## 价值
- 这轮最大的价值不是“又修了一个词”，而是 `platform conversion rant` 终于开始按 **交易前转化阻力** 这件事本身工作了。
- 这意味着：
  - 我们不是在修现象
  - 而是在把一类问题的判断边界真正设计清楚
