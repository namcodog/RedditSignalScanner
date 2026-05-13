# Phase 746

## 发现了什么？

- Phase 745 后，继续按 `1.0` 密度优先口径推进，不再继续抓 Reddit，避免在账号护栏刚落地后继续打 API。
- 发布前真实状态：
  - `published_total = 115`
  - recent30 lane：`signal=13 / hot=11 / breakdown=6`
  - recent30 scope：`AI=11 / 增长=9 / 电商=10`
- 结论很具体：只差一张增长卡，但增长卡发布后会挤出窗口里最老的一张卡，所以必须再次验证，不能靠推测宣布达标。

## 做了什么？

### 1. 补 1 张增长卡

- 发布：
  - `两天促销别急着新建广告计划，老投手更愿意只换素材。`
- 卡片处理重点：
  - 把 Google Ads 短促问题从“后台设置说明”改成“别打碎系统学习数据”的投手经验。
  - 去掉“影响目标、回传信号”这类报告腔。

### 2. 发现窗口挤出偏差

- 增长卡发布后，总卡到 `116`。
- 但 recent30 scope 变成：
  - `AI=11 / 增长=10 / 电商=9`
- 说明这张增长卡挤出的不是 AI，而是一张电商；如果这时停，会留下一个看起来补了增长、实际又亏了电商的新偏差。

### 3. 再补 1 张电商卡

- 从 validate 队列里选了 `r/CleaningTips` 的木质橱柜黏膜清洁帖：
  - 原帖 `1521` 赞、`82` 评论
  - 题材属于家居清洁/小商品，不是之前 EDC/背包线重复
- 发布：
  - `木柜子那层黏膜把人烦坏了，评论区直接把清洁剂配方试出来了。`
- 卡片处理重点：
  - 不写成清洁说明书。
  - 收成“厨房木柜黏膜”这个可选品、可内容化、可反推清洁剂文案的具体痛点。

## 验证结果

- 已发布总卡：
  - `117`
- recent30 lane：
  - `signal=13 / hot=11 / breakdown=6`
- recent30 scope：
  - `AI=10 / 增长=10 / 电商=10`
- mini snapshot 已推送：
  - `release_id = release-07ca3d68ad0c`
  - `card_count = 117`
- 发布真相源已核对：
  - `backend/data/hotpost/releases/latest.json -> release-6972cbbdaf1d`
  - `backend/data/hotpost/releases/release-6972cbbdaf1d/cards = 117`
- 分发 latest 已核对一致：
  - `backend/data/hotpost/mini_snapshots/latest.json = release-07ca3d68ad0c / 117`
  - `miniRelease/data/latest.json = release-07ca3d68ad0c / 117`
  - `miniFavorites/data/latest.json = release-07ca3d68ad0c / 117`

## 还剩什么问题？

- lane 当前不是目标 `18 / 8 / 4`，而是 `13 / 11 / 6`。
- 这不是坏结果：`hot + breakdown` 之前长期不足，现在反而补厚了；`1.0` 阶段优先级是信息密度和领域均衡，不应为了漂亮比例再硬塞 signal。
- 下一轮要做的是继续稳定 `每轮 6+ 张`，并观察 lane 是否自然回到更均衡，而不是立刻反向矫枉过正。

## 下一步

1. 暂停继续抓 Reddit，优先保护 API 和账号。
2. 下一轮从本地队列继续吃电商/增长候选，少碰 AI，避免 scope 再偏回去。
3. 若继续补卡，先看 recent30 挤出窗口明细，再决定补哪个领域，不能只看总量。
4. 继续按 `publish -> push snapshot -> 核对 latest` 做完整闭环。
