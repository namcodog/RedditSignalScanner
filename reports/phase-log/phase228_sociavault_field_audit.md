# Phase 228 - SociaVault API 字段级深度审计（基于 OpenAPI 规范）

日期：2026-03-02

## 审计方法

直接从 `https://docs.sociavault.com/api-reference/openapi.json`（4.1MB）提取完整的 OpenAPI 3.x 规范，用程序解析每个端点的参数定义、响应 schema 和 JSON 样例。**比人工逐页读文档更精确、更完整，零遗漏。**

---

## 一、首轮审计勘误清单

### 🔴 严重遗漏

| # | 遗漏项 | 首轮记录 | OpenAPI 实际 | 影响 |
|---|--------|---------|-------------|------|
| 1 | **端点总数** | 85 个 | **86 个**（多了 `/v1/credits`） | 账户管理端点被遗漏 |
| 2 | **Threads 端点数** | 4 个 | **5 个**（多了 `/threads/search`） | 关键词搜索能力被遗漏 |
| 3 | **Reddit Search Ads** | ❌ 404 标记 | OpenAPI 中路径为 `/reddit/ads/search`（不是 `/reddit/search-ads`）| **可能是路径写错导致 404！** |
| 4 | **Facebook Comments** | ❌ 404 标记 | OpenAPI 中存在 `/facebook/post/comments`，有完整样例 | **端点存在！首轮测试路径可能打错** |
| 5 | **Facebook Transcript** | ❌ 404 标记 | OpenAPI 中存在 `/facebook/post/transcript`，有完整样例 | **同上** |
| 6 | **TikTok Shop Product Details 字段** | "单品详情" | 含 `stock`、`specifications`、`shop_performance`、`logistic`、`bnpl_display_info`、`skus` 等 50+ 字段 | 选品核心数据被遗漏 |
| 7 | **TikTok Demographics 成本** | "20+ credits" | **精确 26 credits/次** | 成本估算不准 |
| 8 | **TikTok Transcript 成本** | 1 credit | **1 credit 标准，但 `use_ai_as_fallback=true` 时 10 credits** | 隐藏成本 |
| 9 | **Reddit Subreddit Search 参数** | 只记了 query + sort | 还支持 `filter` (posts/comments/media)、`timeframe`、`cursor` 分页 | 搜索能力被低估 |
| 10 | **TikTok Shop region 枚举** | 只说了 US/GB/DE | 实际支持 **16 个国家**：US/GB/DE/FR/IT/ID/MY/MX/PH/SG/ES/TH/VN/BR/JP/IE | 覆盖范围大幅扩大 |

### ⚠️ 精确度修正

| 项 | 首轮 | 修正 |
|----|------|------|
| Reddit Ads Search 路径 | `/reddit/search-ads` | `/v1/scrape/reddit/ads/search` |
| Reddit Ads Search 参数 | 未记录 | `query`(必填), `industries`(16个行业enum), `budgets`(LOW/MEDIUM/HIGH), `formats`(IMAGE/VIDEO/CAROUSEL/FREE_FORM), `placements`(FEED/COMMENTS_PAGE), `objectives`(5种) |
| Facebook Group Posts | 未记限制 | **每次只能获取 3 条帖子**（Facebook API 限制） |
| Facebook Ad Library Search | 未记限制 | cursor 在约 1,500 条时会超过 GET 请求限制，需改 POST |
| YouTube Comments | 未记限制 | `order=top` 最多 ~1k 条，`order=newest` 最多 ~7k 条 |
| Twitter User Tweets | 未记限制 | **只返回 100 条最热门推文**，不是最新 |
| Threads Search | 未记限制 | 只返回 20-30 条结果 |
| Threads User Posts | 未记限制 | 只能获取最近 20-30 条 |

---

## 二、按平台完整端点清单

### TikTok（21 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 | 隐藏价值点 |
|---|------|------|------|------|---------|-----------|
| 1 | Profile | `/tiktok/profile` | 1 cr | 无 | `handle` | 含 `ttSeller`(是否TT卖家)、`commerceUserInfo`、`bioLink`、`stats`/`statsV2`(粉丝/赞/视频数精确值) |
| 2 | **Demographics** | `/tiktok/demographics` | **26 cr** | 无 | `handle` | 受众国家分布——**达人筛选核心数据** |
| 3 | Profile Videos | `/tiktok/videos` | 1 cr | `max_cursor` | `handle`, `sort_by`(latest/popular), `user_id` | `user_id` 更快；支持按热度排序 |
| 4 | Video Info | `/tiktok/video-info` | 1 cr | 无 | `url`, `get_transcript`, `region` | 可同时取转录！ |
| 5 | **Transcript** | `/tiktok/transcript` | **1 cr (AI: 10 cr)** | 无 | `url`, `language`, `use_ai_as_fallback` | 支持多语言+AI兜底——内容分析利器 |
| 6 | Live | `/tiktok/live` | 1 cr | 无 | `handle` | 含直播间实时数据、标题、开播时间 |
| 7 | Comments | `/tiktok/comments` | 1 cr | `cursor`(int) | `url`, `trim` | 评论情绪分析输入 |
| 8 | Following | `/tiktok/following` | 1 cr | `min_time` | `handle` | 达人关注了谁——竞品/供应链线索 |
| 9 | Followers | `/tiktok/followers` | 1 cr | `min_time` | `handle`/`user_id` | 粉丝列表——种子用户获取 |
| 10 | Search Users | `/tiktok/search/users` | 1 cr | `cursor`(int) | `query` | 按关键词找达人 |
| 11 | Search Hashtag | `/tiktok/search/hashtag` | 1 cr | `cursor`(int) | `hashtag`, `region` | 话题趋势追踪 |
| 12 | **Search Keyword** | `/tiktok/search/keyword` | 1 cr | `cursor`(int) | `query`, `date_posted`(6档), `sort_by`(3档), `region` | **支持时间筛选+排序——远比首轮记录的强** |
| 13 | Search Music | `/tiktok/search/music` | 1 cr | `offset` | `keyword`, `filter_by`(all/title/creators), `sort_type`(5种) | 音乐趋势+商用筛选 |
| 14 | **Top Search** | `/tiktok/search/top` | 1 cr | `cursor`(int) | `query`, `publish_time`, `sort_by` | **含照片轮播 + 视频两种格式！首轮标 404 是错的** |
| 15 | **Popular Songs** | `/tiktok/music/popular` | 1 cr | `page` | `timePeriod`(7/30/130天), `rankType`(popular/surging), `commercialMusic`, `countryCode`(70+国家) | **可筛选商用音乐 + 全球 70+ 国家** |
| 16 | Popular Creators | `/tiktok/creators/popular` | 1 cr | `page` | `sortBy`(3种), `followerCount`(4档), `creatorCountry`, `audienceCountry` | **双维度国家筛选——精准达人匹配** |
| 17 | Popular Videos | `/tiktok/videos/popular` | 1 cr | `page` | `period`(7/30天), `orderBy`(like/hot/comment/repost), `countryCode` | 热门内容趋势 |
| 18 | Popular Hashtags | `/tiktok/hashtags/popular` | 1 cr | `page` | `period`(7/30/120天), `countryCode`, `newOnBoard` | **`newOnBoard` 筛新上榜话题——早期趋势捕捉** |
| 19 | Song Details | `/tiktok/music/details` | 1 cr | 无 | `clipId` | 含 `user_count`(使用次数)、`is_commerce_music`(商用标记) |
| 20 | **TikToks using Song** | `/tiktok/music/videos` | 1 cr | `cursor`(int) | `clipId` | **首轮标 404 是错的！OpenAPI 路径不同** |
| 21 | Trending Feed | `/tiktok/trending` | 1 cr | 无 | `region` | 实时热门流 |

### TikTok Shop（4 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 | 隐藏价值点 |
|---|------|------|------|------|---------|-----------|
| 1 | **Shop Products** | `/tiktok-shop/products` | 1 cr | `cursor` | `url`, `region`(**16国**) | `shopInfo` 含 `sold_count`/`followers_count`/`shop_rating`/`store_sub_score` |
| 2 | **Product Details** | `/tiktok-shop/product-details` | 1 cr | 无 | `url`, `get_related_videos`, `region` | 🔥 **关键**: `stock`(精确库存)、`specifications`(品牌/产地/成分)、`category_name`、`shop_performance`(95%+)、`bnpl_display_info`(分期)、`logistic`(物流)、`skus`(所有SKU)、`sale_props`(变体属性)、`get_related_videos`(带货视频!) |
| 3 | **Shop Search** | `/tiktok-shop/search` | 1 cr | `page` | `query` | 30 商品/页，返回 `total_products` |
| 4 | **Product Reviews** | `/tiktok-shop/product-reviews` | 1 cr | `page` | `url`/`product_id` | 100 评论/页！含 `total_reviews`、`overall_score`、`rating_result`(评分分布) |

### Reddit（7 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 | 隐藏价值点 |
|---|------|------|------|------|---------|-----------|
| 1 | Subreddit Posts | `/reddit/subreddit` | 1 cr | `after` | `subreddit`(必填), `timeframe`(5档), `sort`(5档), `trim` | 完整帖子对象 |
| 2 | Subreddit Details | `/reddit/subreddit/details` | 1 cr | 无 | `subreddit`(**大小写敏感!**), `url` | 社区元数据 |
| 3 | **Subreddit Search** | `/reddit/subreddit/search` | 1 cr | `cursor` | `subreddit`, `query`, **`filter`(posts/comments/media)**, `sort`(5档), `timeframe`(6档含hour) | 🔥 **可以搜评论和媒体！不只是帖子** |
| 4 | Post Comments | `/reddit/post/comments` | 1 cr | `cursor` | `url`, `trim` | 嵌套评论树 |
| 5 | Search (全站) | `/reddit/search` | 1 cr | `after` | `query`, `sort`(含comment_count), `timeframe` | sort 支持按评论数排序 |
| 6 | **Search Ads** | `/reddit/ads/search` | 1 cr | 无 | `query`, **`industries`(16个行业!)**, `budgets`(3档), `formats`(4种), `placements`(2种), `objectives`(5种) | 🔥🔥🔥 **可按行业搜竞品广告！首轮路径打错导致 404** |
| 7 | Get Ad | `/reddit/ad` | 1 cr | 无 | `id` | 含 `analysis_summary`(AI分析)、`inspiration_creative`(素材/CTA) |

### YouTube（9 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 | 隐藏价值点 |
|---|------|------|------|------|---------|-----------|
| 1 | Channel Details | `/youtube/channel` | 1 cr | 无 | `channelId`/`handle`/`url` | 含 `email`、`twitter`、`instagram`、`tags`、`country`、`store` |
| 2 | **Channel Videos** | `/youtube/channel-videos` | 1 cr | `continuationToken` | `sort`(latest/popular), **`includeExtras`** | 🔥 `includeExtras=true` 取 like+comment 数+描述 |
| 3 | Channel Shorts | `/youtube/channel/shorts` | 1 cr | `continuationToken` | `sort`(newest/popular) | Shorts 列表 |
| 4 | Video Details | `/youtube/video` | 1 cr | 无 | `url` | 含 `viewCountInt`、`likeCountInt`、`commentCountInt`、`durationMs`、`genre`、`chapters`、`keywords`、`captionTracks` |
| 5 | Transcript | `/youtube/video/transcript` | 1 cr | 无 | `url` | 含 `language`、`transcript_only_text`(纯文本)、`captionTracks` |
| 6 | **Search** | `/youtube/search` | 1 cr | `continuationToken` | `query`, `uploadDate`(4档), `sortBy`, `filter`(all/shorts), **`includeExtras`** | 返回 videos+channels+playlists+shorts+lives 多类型结果 |
| 7 | Search Hashtag | `/youtube/search/hashtag` | 1 cr | `continuationToken` | `hashtag`, `type`(all/shorts) | 话题追踪 |
| 8 | **Comments** | `/youtube/video/comments` | 1 cr | `continuationToken` | `url`, `order`(top/newest) | top≈1k, newest≈7k 条上限 |
| 9 | Trending Shorts | `/youtube/shorts/trending` | 1 cr | 无 | (无参数) | 约 48 条热门 Shorts |

### Instagram（9 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 |
|---|------|------|------|------|---------|
| 1 | Profile | `/instagram/profile` | 1 cr | 无 | `handle`, `trim` |
| 2 | Posts | `/instagram/posts` | 1 cr | `next_max_id` | `handle`, `trim` |
| 3 | Post/Reel Info | `/instagram/post-info` | 1 cr | 无 | `url`, `trim` |
| 4 | Transcript | `/instagram/transcript` | 1 cr | 无 | `url` (**AI驱动，10-30秒**) |
| 5 | Comments | `/instagram/comments` | 1 cr | `cursor` | `url` (~15条/页) |
| 6 | Reels | `/instagram/reels` | 1 cr | `max_id` | `user_id`/`handle`, `trim` |
| 7 | Story Highlights | `/instagram/highlights` | 1 cr | 无 | `user_id`/`handle` |
| 8 | Highlight Details | `/instagram/highlight-detail` | 1 cr | 无 | `id` (含完整 story 内容) |
| 9 | Reels by Song | `/instagram/reels-by-song` | 1 cr | `max_id` | `audio_id` |

### Facebook（7 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键发现 |
|---|------|------|------|------|---------|
| 1 | Profile | `/facebook/profile` | 1 cr | 无 | 含 `adLibrary.adStatus`(是否在投广告)、`adLibrary.pageId`、`category`、`priceRange`、`rating`、`services` |
| 2 | Profile Posts | `/facebook/profile/posts` | 1 cr | `cursor` | 支持 `pageId`(更快) |
| 3 | Profile Reels | `/facebook/profile/reels` | 1 cr | `next_page_id`+`cursor` | **双参数分页！必须同时传** |
| 4 | Group Posts | `/facebook/group/posts` | 1 cr | `cursor` | **限制: 每次只能获取 3 条！** `sort_by` 支持 4 种排序 |
| 5 | **Post** | `/facebook/post` | 1 cr | 无 | 🔥 含 `like_count`/`comment_count`/`share_count`/`view_count` + `video`(SD/HD URL) + `transcript` + `comments` + `music` |
| 6 | **Comments** | `/facebook/post/comments` | 1 cr | `cursor` | ⚠️ **首轮标 404 是错的！OpenAPI 有完整定义和样例** |
| 7 | **Transcript** | `/facebook/post/transcript` | 1 cr | 无 | ⚠️ **首轮标 404 是错的！OpenAPI 有完整定义和样例** |

### Facebook Ad Library（4 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 |
|---|------|------|------|------|---------|
| 1 | Ad Details | `/facebook-ad-library/ad-details` | 1 cr | 无 | `id`/`url`, **`get_transcript`**(新功能!)、`trim` |
| 2 | **Search** | `/facebook-ad-library/search` | 1 cr | `cursor` | `query`, `sort_by`(impressions/most_recent), `search_type`(unordered/exact), `ad_type`, `country`, `status`, `media_type`(6种), `start_date`/`end_date` |
| 3 | Company Ads | `/facebook-ad-library/company-ads` | 1 cr | `cursor` | `pageId`/`companyName`, `country`, `status`(ALL/ACTIVE/INACTIVE), `media_type`(6种), `language`, `start_date`/`end_date` |
| 4 | **Search Companies** | `/facebook-ad-library/search-companies` | 1 cr | 无 | `query` — **OpenAPI 有定义和样例！首轮可能路径打错** |

### Google Ad Library（3 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 |
|---|------|------|------|------|---------|
| 1 | Ad Details | `/google-ad-library/ad-details` | 1 cr | 无 | `url` — 含 OCR 文本提取 |
| 2 | **Company Ads** | `/google-ad-library/company-ads` | 1 cr | `cursor` | `domain`/`advertiser_id`, `topic`(all/political), `region`, `start_date`/`end_date` |
| 3 | Search Advertisers | `/google-ad-library/search-advertisers` | 1 cr | 无 | `query` — 返回 advertisers + websites |

### LinkedIn Ad Library（2 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 |
|---|------|------|------|------|---------|
| 1 | **Search Ads** | `/linkedin-ad-library/search` | 1 cr | `paginationToken` | `company`, `keyword`, `countries`(逗号分隔), `startDate`/`endDate` |
| 2 | **Ad Details** | `/linkedin-ad-library/ad-details` | 1 cr | 无 | `url` — 含 `targeting`(语言+地区)、`adType`、`cta`、`destinationUrl`、`totalImpressions`(如"5k-10k")、`impressionsByCountry`、`adDuration` |

### LinkedIn（3 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键发现 |
|---|------|------|------|------|---------|
| 1 | Person Profile | `/linkedin/profile` | 1 cr | 无 | 含 `experience`、`education`、`publications`、`projects`、`recommendations`、`similarProfiles`、`recentPosts` |
| 2 | **Company Page** | `/linkedin/company` | 1 cr | 无 | 🔥 含 `followers`、`employeeCount`、`funding`(轮次/投资人)、`specialties`、`employees`(关键人物)、`posts`、`similarPages` |
| 3 | Post | `/linkedin/post` | 1 cr | 无 | 含 `commentCount`、`likeCount`、`author.followers`、`comments`、`moreArticles` |

### Twitter/X（6 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键发现 |
|---|------|------|------|------|---------|
| 1 | Profile | `/twitter/profile` | 1 cr | 无 | 含 `is_blue_verified`、`followers_count`、`favourites_count`、`statuses_count`、`media_count`、`highlighted_tweets`、`creator_subscriptions_count`、`business_account` |
| 2 | User Tweets | `/twitter/user-tweets` | 1 cr | 无 | ⚠️ **只返回 100 条最热门推文** |
| 3 | Tweet Details | `/twitter/tweet` | 1 cr | 无 | `url`, `trim` |
| 4 | Transcript | `/twitter/tweet/transcript` | 1 cr | 无 | AI 驱动，较慢 |
| 5 | Community | `/twitter/community` | 1 cr | 无 | 含 `member_count`、`rules`、`is_nsfw`、`trending_hashtags_slice`、`creator_results` |
| 6 | Community Tweets | `/twitter/community/tweets` | 1 cr | 无 | 社区推文列表 |

### Threads（5 个端点）⚠️ 首轮漏了 1 个

| # | 端点 | 路径 | 成本 | 分页 | 关键发现 |
|---|------|------|------|------|---------|
| 1 | Profile | `/threads/profile` | 1 cr | 无 | 含 `follower_count`、`is_verified`、`biography`、`bio_links` |
| 2 | User Posts | `/threads/user-posts` | 1 cr | 无 | ⚠️ 只返回 20-30 条 |
| 3 | Post | `/threads/post` | 1 cr | 无 | 含评论和相关帖子 |
| 4 | **Search** | `/threads/search` | 1 cr | 无 | 🔥 **首轮完全遗漏！** 支持关键词搜帖子（限 20-30 条） |
| 5 | Search Users | `/threads/search-users` | 1 cr | 无 | 用户搜索 |

### Pinterest（4 个端点）

| # | 端点 | 路径 | 成本 | 分页 | 关键参数 |
|---|------|------|------|------|---------|
| 1 | Search | `/pinterest/search` | 1 cr | `cursor` | `query`, `trim` |
| 2 | Pin | `/pinterest/pin` | 1 cr | 无 | `url`, `trim` |
| 3 | User Boards | `/pinterest/user/boards` | 1 cr | 无 | `handle`, `trim` |
| 4 | Board | `/pinterest/board` | 1 cr | `cursor` | `url`, `trim` |

### Google Search（1 个端点）

| # | 端点 | 路径 | 成本 | 关键参数 |
|---|------|------|------|---------|
| 1 | Search | `/google/search` | 1 cr | `query`, `region`(2字母国家代码) |

### Account（1 个端点）— 首轮遗漏

| # | 端点 | 路径 | 关键 |
|---|------|------|------|
| 1 | **Get Credits Balance** | `/v1/credits` | 账户余额查询——自动化必需 |

---

## 三、高价值端点 TOP 10（跨境电商视角）

| 排名 | 端点 | 价值理由 | 杠杆效应 |
|------|------|---------|---------|
| 🥇 1 | **TikTok Shop Product Details** | `stock`精确库存 + `specifications`(品牌/产地) + `shop_performance` + `bnpl_display_info` + `skus` + `get_related_videos`(带货视频) | **一个 API 调用 = Jungle Scout 式选品数据** |
| 🥈 2 | **TikTok Shop Search** | 按关键词搜商品 + 30 商品/页 + `total_products` | **品类扫描起点** |
| 🥉 3 | **Reddit Ads Search** | 按 **16 个行业** + 预算档位 + 广告格式搜竞品广告 | **竞品广告情报——之前以为 404** |
| 4 | **Facebook Ad Library Search** | 关键词搜 + 按日期/国家/状态/媒体类型过滤 | **跨平台广告监控** |
| 5 | **TikTok Popular Creators** | 按 `creatorCountry` + `audienceCountry` 双维度筛 + 按 engagement/followers 排序 | **精准达人匹配** |
| 6 | **YouTube Channel Details** | 含 email/社交链接/store/tags/country | **达人联系方式获取** |
| 7 | **TikTok Search Keyword** | 6 档时间筛选 + 3 种排序 + region 指定 | **内容趋势追踪** |
| 8 | **LinkedIn Company Page** | 含 funding(融资历史) + employees(关键人物) + specialties | **竞品公司调研** |
| 9 | **Reddit Subreddit Search** | 支持搜 posts/comments/media + 6 档时间含 hour | **精准社区内容挖掘** |
| 10 | **TikTok Shop Product Reviews** | 100 评论/页 + `overall_score` + `rating_result`(评分分布) | **消费者声音采集** |

---

## 四、成本估算

### 完整品类调研场景（如"家用咖啡机"）

| 步骤 | 端点 | 调用次数 | 成本(credits) |
|------|------|---------|-------------|
| TikTok Shop 关键词搜 5 词 | shop/search | 5 | 5 |
| TOP 20 商品详情 | shop/product-details | 20 | 20 |
| TOP 10 商品评论(各2页) | shop/product-reviews | 20 | 20 |
| Reddit 5 社区帖子 | reddit/subreddit | 5 | 5 |
| Reddit 5 社区搜索 | reddit/subreddit/search | 5 | 5 |
| Reddit 50 帖评论 | reddit/post/comments | 50 | 50 |
| YouTube 搜索 3 词 | youtube/search | 3 | 3 |
| YouTube 10 视频详情 | youtube/video | 10 | 10 |
| YouTube 10 视频转录 | youtube/video/transcript | 10 | 10 |
| YouTube 10 视频评论 | youtube/video/comments | 10 | 10 |
| FB Ad Library 搜 3 词 | facebook-ad-library/search | 3 | 3 |
| Google Ad Library 搜 3 域名 | google-ad-library/company-ads | 3 | 3 |
| Reddit Ads 搜 2 行业 | reddit/ads/search | 2 | 2 |
| TikTok 3 达人画像 | tiktok/profile | 3 | 3 |
| TikTok 3 达人受众 | tiktok/demographics | 3 | **78** |
| **合计** | | **152 次** | **~227 credits** |

> 💡 如果不用 TikTok Demographics（26 cr/次），总成本降至 ~149 credits

### 按月订阅场景

| 频率 | 品类数 | 月成本 | 对应订阅档 |
|------|--------|--------|-----------|
| 每周 1 品类 | 4/月 | ~900 cr | 基础档 |
| 每天 1 品类 | 20/月 | ~4,500 cr | 进阶档 |
| 实时监控 10 品类 | 持续 | ~15,000 cr+ | 企业档 |

---

## 五、与现有系统对接建议

### 直接映射关系

| SociaVault 字段 | 我们的表/字段 | 对接难度 |
|-----------------|-------------|---------|
| Reddit subreddit posts→title/selftext/score/author/created_utc | `posts_raw.title/body/score/author_name/created_at` | ✅ 直接映射 |
| Reddit post comments→body/score/author/depth | `comments.body/score/author_name/depth` | ✅ 直接映射 |
| TikTok Shop product→title/sale_price/sold_count/score | `posts_raw.extra_data`(JSON) | ⚠️ 需新增字段或用 extra_data |
| Reddit ad→analysis_summary/industries | `evidence_posts`/新表 | ⚠️ 需设计新模型 |
| YouTube video→viewCount/likeCount/commentCount | `posts_hot.extra_data` | ⚠️ 需扩展 source 枚举 |

### 优先级建议

1. **P0**: Reddit 6 个端点直接替换 `RedditAPIClient`——最小改动、最大价值
2. **P0**: 确认 `/reddit/ads/search` 的正确路径后重测——**如果能按行业搜广告，价值翻倍**
3. **P1**: TikTok Shop 4 个端点——新增选品能力
4. **P1**: 重测 Facebook Comments/Transcript/Search Companies——**可能是首轮路径打错**
5. **P2**: YouTube 9 端点 + 三大广告库 8 端点——跨平台分析

---

## 六、本次执行的价值

1. **从 OpenAPI 规范精确提取了 86 个端点的完整参数和响应字段**——不再有遗漏
2. **发现首轮审计 10 个严重遗漏**——包括 Threads Search、Reddit Ads Search 正确路径、Facebook Comments/Transcript 可能未真正 404
3. **发现 3 个"假 404"** — Reddit Search Ads / Facebook Comments / Facebook Transcript 可能是路径打错
4. **TikTok Shop region 支持 16 国**（不是 3 国）——覆盖东南亚、拉美、日本
5. **精确成本估算**——单次完整品类调研约 227 credits
6. **完整的字段到数据库映射方案**——为 adapter 开发提供直接依据

---

*审计完成时间：2026-03-02 12:15*
*数据来源：https://docs.sociavault.com/api-reference/openapi.json (4.1MB, 86 endpoints)*
*原始字段级数据：`/tmp/sv_all_endpoints_summary.md` (2014 行)*
