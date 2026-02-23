# Phase 66 - A组12个月 posts 回填补跑

时间：2025-12-22

## 背景
- 12个月 posts 回填 run_id = f6a36768-f25f-4339-9ca7-c6453fadd93f
- 发现 partial/failed 需要补跑

## 执行
- 将补偿 targets（is_compensation=true）中 status=partial 的 117 条重置为 queued
- 重新入队：backfill failed 6 条，compensation 121 条（含 failed 4 + queued 117）
- 入队后队列：compensation_queue=113，backfill_queue=0

## 当前状态快照
- run 总体：completed 691 / failed 4 / partial 458 / queued 109 / running 2
- compensation targets：completed 460 / failed 4 / queued 109 / running 2

## 下一步
- 等 compensation_queue 清零后复查 run 的 failed/partial
- 视情况决定是否继续补跑或收尾

---

## 阶段3-清洗/去重/回填优化（2025-12-22）
- 新增配置：INCREMENTAL_SPAM_FILTER_MODE、INCREMENTAL_COMMENTS_BACKFILL_ENABLED、INCREMENTAL_COMMENTS_BACKFILL_MAX_POSTS、INCREMENTAL_COMMENTS_BACKFILL_DEPTH
- 增量抓取新增：spam tag/allow 模式、内容哈希去重（text_norm_hash）、增量评论回填触发
- 入库 metadata 增加 spam_category 标记
- 新增测试：内容哈希去重、spam tag 保留、评论回填触发
- 测试命令：python -m pytest backend/tests/services/test_incremental_crawler_dedup.py（11 passed）
- 回填默认对齐：mode=smart_shallow、limit=50、depth=2（与 comments.fetch_and_ingest 默认一致）
- spam 默认策略调整为 tag（保留但打标）
- 修复 spam_tag 与 RedditPost(slots) 的兼容性（side map 兜底），并补测试
- 测试库小流量验证：
  - run_id=1edcc4c1-b8ae-4236-8b1f-a1a90914ad41
  - 社区：r/entrepreneur、r/saas、r/sideproject、r/marketing、r/startups
  - 参数：limit=10、sort=hot、time_filter=month
  - 结果：total_inserted=10、spam_tagged=1、comment_tasks=5（send_task 模拟记录）
- 分社区：entrepreneur(0/0/0)、saas(0/0/0)、sideproject(0/0/0)、marketing(0/0/0)、startups(10/0/0)
- 生产库小流量验证：
  - run_id=a54b266b-2762-40ec-81f1-61a6a12e55a4
  - 社区：r/shopifyappdev、r/amazonargentina、r/entrepreneur、r/amazonmerch、r/shopifyseo
  - 参数：limit=10、sort=hot、time_filter=month
  - 结果：total_inserted=22、spam_tagged=0、comment_tasks=13（send_task 模拟记录）
  - 分社区：shopifyappdev(3/0/0)、amazonargentina(3/0/0)、entrepreneur(8/0/0)、amazonmerch(3/0/0)、shopifyseo(5/0/0)
