# 阶段1 数据体检记录（数据挖掘SOP）

时间：当前本地库直接查询（postgresql://localhost:5432/reddit_signal_scanner，使用 backend/.env）

## 1. 基准规模与时间范围
- posts_raw is_current=true：85,067 条
- posts_raw 时间：2013-02-26 → 2025-11-26
- comments 总数：1,056,076 条
- comments 时间：2013-09-10 → 2025-11-19
- 近30天：posts_raw 19,992；comments 239,721
- 近90天：posts_raw 36,253；comments 397,120

## 2. 空值与覆盖
- posts_raw：title 0；body 空 22,595（≈25%）；score/subreddit/author_name 0
- comments：body/score/depth/parent_id/subreddit 均无空
- 标签覆盖：content_labels 对 comment 去重 959,362 vs comments 1,056,076（覆盖率≈90.9%）

## 3. 社区概览（community_pool）
- tier 统计：t2=11、medium=11、semantic=23、high=48
- semantic_quality_score 均值=0.5（各 tier 相同，疑似默认值未校准）

## 4. 社区抓取质量（community_cache × pool 分组均值）
- high：avg_valid_posts≈12.58，dedup_rate≈0.21，empty_hit≈0.25，success_hit≈2.23
- medium：avg_valid_posts≈0，dedup_rate≈0.24，empty_hit≈0，success_hit≈1.82
- semantic：avg_valid_posts≈0，empty_hit≈1.0
- t2：缺少抓取数据
结论：高价值组仍有重复率偏高，其他组抓取几乎空白，需重算质量分并校准调度。

## 5. 痛点TOP
- aspect 前7：subscription 41,012；other 37,051；price 5,941；content 3,033；install 1,589；strength 99；ecosystem 47
- 社区痛点TOP15（category='pain'，按评论的 subreddit 聚合）：amazonprime 10,301；amazonflexdrivers 4,671；peopleofwalmart 3,680；etsy 3,575；aliexpress 2,763；facebookads 2,462；amazonecho 2,407；amazonseller 2,241；fulfillmentbyamazon 2,123；etsysellers 1,955；amazonemployees 1,897；legomarket 1,892；fascamazon 1,793；amazon 1,733；aliexpressbr 1,566。每社区主痛点多为 other/subscription，少数为 content。

## 6. 关键结论（阶段1输出）
- 数据新鲜且覆盖高：近90天仍有稳定增量，标签覆盖≈91%，可直接做痛点/竞品分析。
- 质量短板：semantic_quality_score 全部 0.5；非 high 组抓取几乎为空，high 组 dedup_rate ≈21%，需重算评分+调度。
- 痛点重心：订阅、价格、内容/安装体验，集中在电商/亚马逊生态相关社区。

## 7. 下一步（进入阶段2）
- 用 `backend/app/services/community_metrics.py` 公式重算每个社区 C分，应用 `schemas/admin/community.py` 的门槛。
- 用 `community_cache.get_priority_score()` 排调度队列，重点关注 dedup_rate 高的高分社区和未抓取社区。
- 产出：新社区榜单（C分+红黄绿）、异常清单（高重复/空抓）、提级/降频建议，记录到 phase-log。
