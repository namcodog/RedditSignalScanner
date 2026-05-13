# Phase 587 - 压低 rant 首屏里的 help / 求助式弱帖子

## 本轮目标

继续按算法口径收 `rant` 首屏排序，不新增新层，不碰 `trending / opportunity`。

目标只有一个：

- 把“只有求助味、没有强痛点”的帖子从首屏前排往后压

## 改动

- 文件：
  - `backend/app/services/hotpost/evidence_collection_workflow.py`
- 新增一层很薄的排序惩罚：
  - `help / how to / need help` 类帖子，如果没有足够强的 `rant focus signal`
  - 会被额外减分
- 规则保持保守：
  - 只有 `focus_score < 3` 才触发
  - 所以“问题很硬但带问句”的帖子不会被误伤

## 测试

- 新增：
  - `test_collect_hotpost_evidence_demotes_help_style_rant_posts_without_strong_loss_signal`
- 定向回归：
  - `34 passed`
- 更宽 hotpost 回归：
  - `96 passed`

## live 无缓存

- query：
  - `为什么tiktok上做的内容有流量但却没有转化购买？`
- 本轮结果：
  - `status=completed`
  - `mode_state=standard`
  - `evidence_count=5`
  - `communities=["TikTokAds","TikTokshop"]`

### 首屏排序变化

上一轮：

1. `How to attribute WhatsApp Conversions to tiktok ads (help)`
2. `Running Tiktok Ads For The First Time Ever...`
3. `High CTR (14%+) on TikTok Ads but 0 Sales After 24h...`

这一轮：

1. `Running Tiktok Ads For The First Time Ever...`
2. `High CTR (14%+) on TikTok Ads but 0 Sales After 24h...`
3. `How to attribute WhatsApp Conversions to tiktok ads (help)`

## 结论

这轮说明方向是对的：

- `help` 弱帖子没有被粗暴删除
- 但已经不再霸占第一位
- 首屏开始更像“问题判断页”，而不是“社区提问汇总”

## 下一步

1. 继续补 `rant` 的动作建议闭环
2. 让结果不只会说“问题是真的”
3. 还要能说“先动哪一刀”
