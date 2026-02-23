# 阶段2 社区质量重算（草稿）

方法：
- 用 posts_raw 近7天发帖数作为 hit_7d（社区名 r/xxx 映射 subreddit 小写）。
- freshness：last_crawled_at 距今小时。
- dup_ratio：dedup_rate/100（表值是百分数）。
- topic_score：crawl_quality_score（缺省0.5，需后续用真实主题/标注分替换）。
- 评分公式沿用 `backend/app/services/community_metrics.py`：C=0.35*topic% +0.25*activity +0.20*freshness +0.10*(1-spam) +0.10*(1-dup)。MustGates：freshness<=48h、hit_7d>=30、dup<=15%、topic>=0.60。

汇总：
- 状态计数：green 0 / yellow 11 / red 82（主要因 hit_7d<30 或 topic_score=0.5<0.6）。
- 中位 freshness：≈35小时（抓取不算老），瓶颈在命中量/质量分。

Top15（按C分）：
- yellow：r/SpellcasterReviews(78.3, hit7=51, dup=0), r/dropshipping(70.6, hit7=53, dup=66.7), r/ShopifyeCommerce(63.0, hit7=36, dup=83.3), r/DropshippingTips(61.1, hit7=35, dup=0), r/Flipping(60.0, hit7=38, dup=14.3), r/walmart(59.6, hit7=36, dup=8.3)…
- red 高分组多因命中低/dup高，例如 r/Aliexpress(hit7=？ dup=50)、r/FulfillmentByAmazon(hit7=29 dup=75)。

异常清单：
- 高重复（dedup_rate>30%）：r/ecommercemarketing, r/AmazonFBATips, r/Dropshipping_Guide (100%)；r/ShopifyeCommerce, r/shopifyDev (83%)；r/FulfillmentByAmazon (75%)；r/dropshipping, r/MerchByAmazon (66%)；r/amazonecho(60%)；r/fuckamazon(57.9%)；r/amazonprime, r/Aliexpress(50%)；r/shopify(42.9%)。
- 空抓取 empty_hit>0：r/AmazonWFShoppers(7,0), r/AntiAmazon(4,0) 等 13 个社区；需核查爬取是否失效或社区已死。

结论/动作：
1) 质量分未用真实 topic_score，需用标签/实体/痛点密度替换 crawl_quality_score=0.5，避免全体被 topic 门槛卡住。
2) 命中量门槛（hit_7d>=30）可改为按分位数动态阈值，或用评论量近7天替代，防止活跃小社区被“一刀切”判红。
3) 高 dedup 社区要么去重策略有问题，要么抓取重复；先降频或修正去重，再回填。
4) empty_hit>0 的社区需要探针抓取或直接降权，避免浪费抓取额度。

### 用真实“痛点/评分”替换 topic_score 的试算
- topic_score 新算法：pain_rate（近90天，痛点数/评论数，50%映射为1）与评论均分（均分/20封顶1）各占50%，裁剪到0~1。
- 命中改用近7天评论数；其余权重不变。
- 结果：高分仍多为红牌，主因 hit_7d=0 或 <30，或 dedup 高；说明命中阈值过硬或 7 天内该社区无评论/映射缺口。
- Top样例（含 pain/score 真实 topic_score）：  
  - r/AmazonWFShoppers c=54.1，topic=0.53，hit7=0，pain_rate=50%，freshness高；判红因 hit7=0。  
  - r/EtsySellers c=44.7，topic=0.29，hit7=0，pain_rate≈10.8%，avg_score≈7.2。  
  - r/Legomarket c=43.1，topic=0.24，hit7=0，pain_rate≈21.3%。  
  - 其他高痛点社区类似，hit7=0 导致颜色为红。
- 额外计数：仍是 red=93；说明 7 天命中门槛不适合当前分布，可改用 30 天评论量/分位阈值。

### 调整建议（算法合理性）
- 命中阈值：改用近30天评论量分位（如P50或P60）或设最低=10，避免 hit7=0 直接判死；也可用近30天代替7天。
- topic_score：继续用痛点/评分密度替代默认0.5，后续可加入实体覆盖率或高分痛点评分。
- 重复/空抓：保持扣分，先降频或修去重；empty_hit 社区先探针再决定降权。

### 30天窗口重算（更宽松命中阈值）
- 命中用近30天评论数，activity=min(hit30/50,1)；hits_ok=hit30>=20；topic_score仍用痛点率+评分。
- 结果：yellow 59 / red 34（分布更健康）。
- Top15（按C分，含痛点/评分）：  
  - r/EtsySellers c=69.7 (hit30=6,289, dedup=0, topic=0.29, pain率≈10.8%, avg_score≈7.2)  
  - r/Legomarket c=68.0 (hit30=835, dedup=0, topic=0.24, pain率≈21.3%)  
  - r/SpellcasterReviews c=66.3 (hit30=1,457, dedup=0, topic=0.16, pain率≈10.8%)  
  - r/AmazonFlexDrivers c=64.3 (hit30=22,184, dedup=0, topic=0.13, pain率≈4.4%)  
  - 其余见原始SQL（FBA/Aliexpress/ShopifyeCommerce 等多数为黄牌，高重复者仍在名单内）。
- 说明：放宽到30天后，仍可区分高命中社区，同时保留对高重复的扣分。

### 已执行的数据库更新（不改历史，只写入评分/分层）
- 已批量更新 `community_cache.crawl_quality_score` 为新的 topic_score（痛点率+评分），并按当前规则写入 `quality_tier`：
  - 规则：dedup>30% 或 empty_hit>0 或 hit30<20 → t3；其余按 C分排名前15 → t1；其余 → t2。
  - 更新后计数：t1=10，t2=28，t3=44。t1示例：EtsySellers, Legomarket, SpellcasterReviews, AmazonFlexDrivers, bigseo, WalmartCanada, FacebookAds, dropship, AmazonWTF, AmazonSeller。
- 约束：未删除或改历史内容，只更新评分/分层字段，便于调度和抓取优先级使用。
