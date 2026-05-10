# Phase 745

## 发现了什么？

- 这轮继续按 `1.0` 密度优先口径推进，不再补 AI，转而专门补电商和增长。
- 真实已发布总卡从 `102 -> 108`。
- 新发了 `6` 张：
  - 电商 `hot` 1 张
  - 电商 `signal` 3 张
  - 增长 `signal` 2 张
- 当前最近 `30` 张真实窗口：
  - lane：`signal=17 / hot=9 / breakdown=4`
  - scope：`AI=14 / 增长=9 / 电商=7`
- 结论很清楚：
  - lane 结构已经基本稳住，`hot + breakdown` 没再掉回去
  - 领域结构仍然偏 AI，电商虽然回升，但还没到 `10`

## 这轮做了什么？

### 1. 电商卡补量

- 发布了：
  - `EDC 这帖会火，不是大家突然不爱背包了，而是越来越多人嫌包总比今天要带的东西大一圈。`
  - `算 Facebook 和 Google 广告账时，卖家开始把 ROAS 先放一边。`
  - `通勤包买到 28L 才发现，很多人每天根本用不上这么大的包。`
  - `买小挎包时，很多人最后卡住的不是品牌，而是 2.5L 还是 5L。`

### 2. 增长卡补量

- 发布了：
  - `把流量托给第三方前，站长先开始盯 70/30 这种分成到底值不值。`
  - `做 GEO 的人开始先拿静态站试水，看 AI 会不会真的引用自己的内容。`

### 3. 文案去 AI 味

- 不再直接吃自动 draft。
- 手工收掉标题、`summary_line`、`why_now` 和 `detail` 里的解释腔，统一往“转给朋友看”的方向改。
- 重点去掉：
  - 汇报腔
  - “说明 / 值得关注 / 讨论已经从” 这类模板味
  - 过度概括的大词

### 4. 1.0 门禁继续放宽一格

- `config/card_content_rules.yaml`
  - 去掉全局禁词 `帖子里大家`
- 这一步的目的不是放水帖，而是去掉会把正常 `1.0` 草稿卡死的老门禁。

## 验证结果

- `python backend/scripts/hotpost/review_cards.py publish ...`
  - 成功发布 6 张卡
- `python backend/scripts/hotpost/push_mini_snapshot.py`
  - 返回新 release：`release-80a292fe0fe2`
  - `card_count = 108`
- `build_lane_mix_snapshot(load_published_cards())`
  - `{'signal': 17, 'hot': 9, 'breakdown': 4}`
- `build_scope_mix_snapshot(load_published_cards())`
  - `{'ai-automation': 14, 'business-growth-ops': 9, 'ecommerce-sellers': 7}`

## 还剩什么问题？

- lane 结构基本稳定，但还不是理想值：
  - 目标：`18 / 8 / 4`
  - 当前：`17 / 9 / 4`
- 领域结构还没拉平：
  - 目标：`10 / 10 / 10`
  - 当前：`14 / 9 / 7`
- 电商供给已经恢复，但仍然不够厚；很多新候选会撞到已发布老卡。

## 下一步

1. 继续补电商，不再补 AI。
2. 优先找新的电商 `hot / breakdown`，而不是再堆电商 `signal`。
3. 把增长再补 `1` 张，让最近 `30` 张先达到 `10`。
4. 然后再继续推电商，把 `7` 往 `10` 拉。
