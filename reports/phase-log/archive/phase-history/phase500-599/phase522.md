# Phase 522 - Hotpost 冷启动时延校准与收口边界

时间：2026-03-27

## 本轮目标

确认 Hotpost 第二阶段轻量方案在真实冷启动下的表现，判断是否还值得继续在模块内部追加小补丁。

## 发现了什么

### 1. 热路径已经够用

缓存命中时，三模式都能在约 1 秒内返回：

- `trending`
- `rant`
- `opportunity`

而且：

- `queued -> completed` 正常
- `report_source = llm`
- reasoning 触发也正常

### 2. 冷路径并不均匀

冷启动 timing probe 结果：

- `trending / "tiktok shop seller fees"`：
  - `38.32s`
  - `completed`
  - `evidence_count = 30`
- `opportunity / "reddit post scheduler for brands"`：
  - `30.24s`
  - `completed`
  - `evidence_count = 26`
  - reasoning 正常触发
- `rant / "shopify plugin bug complaints"`：
  - 超过 `45s` 观察窗
  - 当时仍停在 `queued`
  - 后续落地为 `degraded`
- `rant / "shopify app crash frustration"`：
  - `45.61s`
  - `completed`
  - `evidence_count = 30`

结论很清楚：

> 当前唯一明显的冷启动短板是 `rant`。

### 3. 已验证不是“评论抓取太深”这一层为主

这轮补了两个很小的收轻动作：

- 低样本 `rant` 只抓少量帖子评论
- `rant` 首轮 scout 只探一个 subreddit，不先双社区起跑

这些改动都通过了定向测试，但 live 冷启动仍接近 `45s`。

这说明：

> 现在的主瓶颈仍更像 Reddit 搜索阶段，而不是评论抓取阶段。

## 是否需要继续修

要修，但**不建议继续在 Hotpost 模块内部堆更多小补丁**。

原因：

- 这轮已经证明：
  - 再补小节流，收益很有限
  - 热路径已够用
  - 冷路径里真正慢的是 `rant` 的 Reddit 搜索阶段
- 如果继续在 Hotpost 里堆局部规则，代码会越来越碎，但收益不高

## 这轮实际执行

### 已落地的小优化

- `reddit_acquisition.py`
  - 新增 `resolve_comment_post_limit(...)`
  - `rant` 首轮 scout 改成单社区起跑
- `evidence_collection_workflow.py`
  - 低样本 `rant` 收轻评论抓取
- 新增定向测试：
  - `test_collect_hotpost_evidence_reduces_rant_comment_fetch_for_low_samples`
  - `test_build_reddit_acquisition_plan_keeps_rant_scout_to_one_subreddit`

### 验证

- `pytest backend/tests/services/hotpost/test_hotpost_reddit_acquisition.py backend/tests/services/hotpost/test_evidence_collection_workflow.py backend/tests/services/hotpost/test_hotpost_search_workflow.py -q`
- 结果：`17 passed`

## 当前结论

- Hotpost 第二阶段现在可以定义为：
  - **功能上完成**
  - **热路径够用**
  - **冷 `rant` 仍是唯一明显时延短板**
- 在“保持模块轻量、不工程化”的约束下，这里已经接近最佳停点。

## 下一步系统性计划

不继续在 Hotpost 内部做更多局部节流。

更合理的下一步只有两条：

1. 如果业务上能接受：
   - 维持当前 Hotpost 方案
   - 把 `rant` 冷启动偏慢作为已知边界

2. 如果业务上不能接受：
   - 下一刀就不能再是 Hotpost 小补丁
   - 而要去 Reddit 搜索执行层 / 网络代理层做更上游的时延治理

## 价值

这轮最大的价值不是“又快了多少”，而是把边界钉死了：

> Hotpost 继续小修，已经开始进入低收益区。

这能避免后面为了追一个非主业务模块，把代码越修越重。
