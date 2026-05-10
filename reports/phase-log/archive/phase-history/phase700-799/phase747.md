# Phase 747

## 发现了什么？

- 这轮只从本地候选和现有 draft 里出卡，没有新增 Reddit 抓取，避免继续消耗 API 和账号风险。
- 本地队列里有不少“看起来在队列里、其实已经发布过”的候选，所以不能照 queue 原样发，必须先按 `card-<candidate_id>-validate` 做已发布去重。
- 当前 recent30 的挤出顺序是 `AI / AI / 增长`，所以如果想在加密信息的同时保持领域均衡，本轮最合理的新增组合是 `AI / AI / 增长`。

## 做了什么？

### 1. 发布 3 张本地卡

- AI：
  - `有人拿 GrapheneOS 盯 ChatGPT，最后得出的结论是：别把它当私人日记本。`
- 增长：
  - `新手接到 Google Ads 客户后，评论区第一反应不是教投放，而是先让他做账户体检。`
- AI：
  - `浏览器代理跑到生产环境后，大家算的不是月费，而是谁来半夜修容器。`

### 2. 过滤掉不适合硬上的候选

- `cand-business-growth-ops-1sgfyle` 被质量门禁拦住：
  - `single_thread_weak_evidence`
  - `single_community_weak_evidence`
- `cand-ai-automation-1sfoaf4` 第一次 seed 失败是 Gemini `503`，不是内容问题；稍后重试成功。
- 电商里有强候选，但这轮如果继续补电商，会把刚打平的领域窗口推偏，所以先不硬发。

### 3. 文案继续按 1.0 口径收

- 不吃自动稿里的报告腔。
- 把 `GrapheneOS / ChatGPT` 收成“别把云端 AI 当私人日记本”。
- 把 `Google Ads beginner` 收成“先做账户体检，不要上来就乱改”。
- 把 `Browserbase vs Browserless` 收成“生产环境里自建浏览器代理的维护账”。

## 验证结果

- 已发布总卡：
  - `120`
- recent30 lane：
  - `signal=16 / hot=8 / breakdown=6`
- recent30 scope：
  - `AI=10 / 增长=10 / 电商=10`
- 发布真相源：
  - `backend/data/hotpost/releases/latest.json -> release-154c7f6a44c0`
  - `cards = 120`
- mini snapshot：
  - `release-dfb386a7784c / 120`
- bundled latest 已核对一致：
  - `miniRelease/data/latest.json = release-dfb386a7784c / 120`
  - `miniFavorites/data/latest.json = release-dfb386a7784c / 120`

## 下一步

1. 继续从本地候选吃，不急着重新抓 Reddit。
2. 下一轮优先看电商强候选，但要先算 recent30 挤出顺序，避免把 `10 / 10 / 10` 又推歪。
3. 如果要补 hot/breakdown，只补明显非重复、可读性强的，不为比例硬发。
