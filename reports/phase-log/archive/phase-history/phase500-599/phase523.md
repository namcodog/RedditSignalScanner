# Phase 523 - Hotpost 上游最小对照诊断

## 背景

- 用户要求先判断冷 `rant` 慢，到底是 Reddit API 问题，还是代理问题。
- 约束：严格保护 Reddit API，只做最少量对照请求，不做高频探测。

## 本轮执行

### 1. 轻量上游优化落地

- `backend/config/hotpost_quality.yaml`
  - 新增 `reddit_guardrails.search_request_timeout_seconds: 15`
- `backend/app/services/hotpost/service.py`
  - `HotpostService` 构造 `RedditAPIClient` 时显式传入 `search_timeout`
- `backend/app/services/infrastructure/reddit_client.py`
  - 搜索请求支持独立 `timeout_seconds`
  - `search_posts / search_subreddit_page / search_subreddits` 走 `search_timeout`

### 2. 测试补齐

- `backend/tests/services/hotpost/test_hotpost_runtime_config.py`
  - 补配置读取与 env 覆盖断言
- `backend/tests/services/crawl/test_reddit_search_client.py`
  - 断言 subreddit search 会把 `timeout_seconds=self.search_timeout` 传入底层请求
- `backend/tests/services/hotpost/test_hotpost_search_service.py`
  - 补 `HotpostService` 将 `search_timeout` 传进 `RedditAPIClient` 的定向测试

### 3. 最小对照实验

仅做极少量对照请求，分别测试：

- `direct`：不走代理
- `trust_env`：沿用当前 `aiohttp trust_env=True`
- `explicit_proxy`：显式传 `http://127.0.0.1:59527`

每种方式只做：

- 1 次 token 获取
- 1 次小搜索（`r/smallbusiness`, `q=shopify app freeze`, `limit=5`）

## 结果

### 定向测试

- `pytest backend/tests/services/hotpost/test_hotpost_runtime_config.py backend/tests/services/crawl/test_reddit_search_client.py backend/tests/services/hotpost/test_hotpost_search_service.py -q`
  - `9 passed`
- `pytest backend/tests/services/infrastructure/test_reddit_client.py backend/tests/services/infrastructure/test_reddit_client_proxy.py -q`
  - `6 passed`

### 对照实验结果

- `direct`
  - token: `200`, `0.61s`
  - search: `200`, `0.79s`
- `trust_env`
  - token: `200`, `0.60s`
  - search: `200`, `0.73s`
- `explicit_proxy`
  - token: `200`, `0.62s`
  - search: `200`, `0.75s`

## 结论

### 1. 发现了什么？

- Reddit API 基础可用性没有问题。
- 代理基础连通性也没有问题。
- 冷 `rant` 的慢，不是“Reddit API 本身慢”或“代理本身断了”这种一级故障。
- 更像是 Hotpost 工作流里的多段串行抓取/补证/生成，把耗时叠高了。

### 2. 是否需要修复？

- 需要。
- 但优先级已经改变：
  - 不是先修 Reddit API
  - 不是先修代理基础连通
  - 而是回到 Hotpost 工作流本身，定位 `rant` 哪一段 fanout/等待最重

### 3. 精确修复方法

- 保留本轮已落地的 `search_timeout`
- 下一步对 `rant` 做阶段耗时拆账：
  - `query resolve`
  - `scout`
  - `expand`
  - `comments`
  - `summary`
  - `report`
- 先找出真正拖时延的那一段，再决定要不要进一步收 `rant` 的首轮 fanout

### 4. 下一步系统性计划

- 先做 `rant` 的阶段耗时观测
- 再决定是否继续收轻 acquisition
- 输出层“结果够硬”问题延后，保持当前顺序：
  - 先上游
  - 后输出

### 5. 这次执行的价值

- 已经排除了两个最容易误判的方向：
  - 不是 Reddit API 整体异常
  - 不是代理链基础不可用
- 这样后面的优化可以更聚焦，也更安全，不会拿 Reddit API 做无意义试探
